import { fetchAllRestaurants } from '@/lib/supabase';

export async function GET() {
  try {
    const rows = await fetchAllRestaurants();
    const all: string[] = [];
    for (const r of rows) {
      if (Array.isArray(r.cuisines)) all.push(...r.cuisines);
    }
    const cuisines = [...new Set(all.filter(Boolean))].sort();
    return Response.json({ cuisines });
  } catch (err) {
    console.error('[/api/cuisines]', err);
    return Response.json({ error: 'Failed to load cuisines' }, { status: 500 });
  }
}
