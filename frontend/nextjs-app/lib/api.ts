const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? '/api';

export interface Recommendation {
  rank: number;
  name: string;
  cuisine: string;
  rating: number | null;
  estimated_cost: string;
  explanation: string;
}

export interface RecommendResponse {
  status: 'success' | 'fallback';
  total_candidates: number;
  filters_relaxed: boolean;
  llm_used: boolean;
  message: string | null;
  recommendations: Recommendation[];
  query: {
    city: string;
    budget_max: number;
    cuisines: string[];
    min_rating: number;
    extra_prefs: string;
  };
}

export interface RecommendRequest {
  city: string;
  budget_max: number;
  cuisines: string[];
  min_rating: number;
  extra_prefs?: string;
}

export async function fetchLocations(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/locations`, { cache: 'no-store' });
  if (!res.ok) throw new Error('Failed to fetch locations');
  const data = await res.json();
  return data.cities as string[];
}

export async function fetchCuisines(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/cuisines`, { cache: 'no-store' });
  if (!res.ok) throw new Error('Failed to fetch cuisines');
  const data = await res.json();
  return data.cuisines as string[];
}

export async function fetchHealth(): Promise<{ status: string; dataset_loaded: boolean; llm_provider: string }> {
  const res = await fetch(`${API_BASE}/health`, { cache: 'no-store' });
  if (!res.ok) throw new Error('API not reachable');
  return res.json();
}

export async function recommend(req: RecommendRequest): Promise<RecommendResponse> {
  const res = await fetch(`${API_BASE}/recommend`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });

  if (res.status === 404) {
    const err = await res.json();
    throw new Error(err.detail ?? 'No restaurants found.');
  }
  if (res.status === 422) {
    throw new Error('Invalid request. Check your inputs.');
  }
  if (!res.ok) {
    throw new Error(`API error ${res.status}`);
  }
  return res.json();
}
