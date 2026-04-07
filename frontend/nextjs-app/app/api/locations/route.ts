import { fetchAllRestaurants } from '@/lib/supabase';

export async function GET() {
  try {
    const rows = await fetchAllRestaurants();
    const cities = [...new Set(rows.map((r) => r.location).filter(Boolean))].sort();
    return Response.json({ cities });
  } catch (err) {
    console.error('[/api/locations]', err);
    return Response.json({ error: 'Failed to load locations' }, { status: 500 });
  }
}
