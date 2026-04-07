import { fetchAllRestaurants, type DBRestaurant } from '@/lib/supabase';

const GROQ_URL = 'https://api.groq.com/openai/v1/chat/completions';
const GROQ_MODEL = 'llama-3.1-8b-instant';
const TOP_N = 15;

interface RecommendRequest {
  city: string;
  budget_max: number;
  cuisines: string[];
  min_rating: number;
  extra_prefs?: string;
}

// ── Filter ────────────────────────────────────────────────────────────────────

function filterRestaurants(rows: DBRestaurant[], req: RecommendRequest): DBRestaurant[] {
  const cityLower = req.city.toLowerCase();

  // Locality match (exact first, then partial)
  let subset = rows.filter((r) => r.location.toLowerCase() === cityLower);
  if (subset.length === 0) {
    subset = rows.filter((r) => r.location.toLowerCase().includes(cityLower));
  }

  // Budget filter
  subset = subset.filter(
    (r) => r.approx_cost === null || r.approx_cost <= req.budget_max
  );

  // Rating filter
  if (req.min_rating > 0) {
    subset = subset.filter((r) => r.rating === null || r.rating >= req.min_rating);
  }

  // Cuisine filter (fuzzy: check if any requested cuisine is in the restaurant cuisines)
  if (req.cuisines.length > 0) {
    const wanted = req.cuisines.map((c) => c.toLowerCase());
    subset = subset.filter((r) =>
      r.cuisines.some((c) => wanted.some((w) => c.includes(w) || w.includes(c)))
    );
  }

  // Relax if too few results
  if (subset.length < 3) {
    let relaxed = rows.filter((r) => r.location.toLowerCase() === cityLower || r.location.toLowerCase().includes(cityLower));
    relaxed = relaxed.filter((r) => r.approx_cost === null || r.approx_cost <= req.budget_max * 1.3);
    if (relaxed.length > subset.length) subset = relaxed;
  }

  // Sort by rating desc, take TOP_N
  return subset
    .sort((a, b) => (b.rating ?? 0) - (a.rating ?? 0))
    .slice(0, TOP_N);
}

// ── LLM ───────────────────────────────────────────────────────────────────────

function buildPrompt(req: RecommendRequest, candidates: DBRestaurant[]): [string, string] {
  const systemPrompt = `You are an expert restaurant recommendation assistant for India.
Rank the provided restaurants based on how well they match the user's preferences.
Always respond in valid JSON only — no markdown, no extra text.`;

  const candidatesJson = JSON.stringify(
    candidates.map((r) => ({
      name: r.name,
      location: `${r.location}, ${r.city}`,
      cuisines: r.cuisines.join(', '),
      rating: r.rating,
      approx_cost_for_two: r.approx_cost ? `₹${r.approx_cost}` : 'N/A',
      rest_type: r.rest_type,
      book_table: r.book_table,
      online_order: r.online_order,
    })),
    null,
    2
  );

  const userPrompt = `User Preferences:
- Location: ${req.city}
- Cuisine(s): ${req.cuisines.length > 0 ? req.cuisines.join(', ') : 'Any'}
- Max Budget: ₹${req.budget_max} for two people
- Minimum Rating: ${req.min_rating} / 5
- Additional Preferences: ${req.extra_prefs || 'None'}

Candidate Restaurants (choose and rank your TOP 5):
${candidatesJson}

Respond ONLY with a JSON array:
[
  {
    "rank": 1,
    "name": "Restaurant Name",
    "cuisine": "Primary Cuisine",
    "rating": 4.3,
    "estimated_cost": "₹600 for two",
    "explanation": "2-3 sentence explanation of why this fits the user's needs"
  }
]`;

  return [systemPrompt, userPrompt];
}

function parseGroqResponse(raw: string) {
  // Strip markdown fences if present
  const text = raw.replace(/```json\s*/g, '').replace(/```\s*/g, '').trim();
  const parsed = JSON.parse(text);
  if (!Array.isArray(parsed)) throw new Error('Expected array');
  return parsed;
}

// ── Route handler ─────────────────────────────────────────────────────────────

export async function POST(req: Request) {
  try {
    const body: RecommendRequest = await req.json();

    if (!body.city || !body.budget_max) {
      return Response.json({ error: 'city and budget_max are required' }, { status: 422 });
    }

    const allRows = await fetchAllRestaurants();
    const candidates = filterRestaurants(allRows, body);

    if (candidates.length === 0) {
      return Response.json({ error: 'No restaurants found for this location.' }, { status: 404 });
    }

    const groqKey = process.env.GROQ_API_KEY;
    let recommendations = null;
    let llmUsed = false;

    if (groqKey) {
      try {
        const [systemPrompt, userPrompt] = buildPrompt(body, candidates);
        const groqRes = await fetch(GROQ_URL, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${groqKey}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            model: GROQ_MODEL,
            messages: [
              { role: 'system', content: systemPrompt },
              { role: 'user', content: userPrompt },
            ],
            temperature: 0.3,
            max_tokens: 1500,
          }),
        });

        if (groqRes.ok) {
          const groqData = await groqRes.json();
          const rawText = groqData.choices?.[0]?.message?.content ?? '';
          recommendations = parseGroqResponse(rawText);
          llmUsed = true;
        }
      } catch (err) {
        console.error('[recommend] LLM error, using fallback:', err);
      }
    }

    // Fallback: top-5 filter results
    if (!recommendations) {
      recommendations = candidates.slice(0, 5).map((r, i) => ({
        rank: i + 1,
        name: r.name,
        cuisine: r.cuisines.join(', ') || '—',
        rating: r.rating ?? 0,
        estimated_cost: r.approx_cost ? `₹${r.approx_cost} for two` : 'N/A',
        explanation: '',
      }));
    }

    return Response.json({
      status: 'success',
      total_candidates: candidates.length,
      filters_relaxed: false,
      llm_used: llmUsed,
      message: null,
      recommendations,
      query: body,
    });
  } catch (err) {
    console.error('[/api/recommend]', err);
    return Response.json({ error: 'Internal server error' }, { status: 500 });
  }
}
