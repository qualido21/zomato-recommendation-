import { createClient } from '@supabase/supabase-js';

const url = process.env.SUPABASE_URL!;
const key = process.env.SUPABASE_KEY!;

export function getSupabase() {
  return createClient(url, key);
}

export interface DBRestaurant {
  id: number;
  name: string;
  city: string;
  location: string;
  cuisines: string[];
  rating: number | null;
  votes: number;
  approx_cost: number | null;
  budget_tier: string;
  rest_type: string;
  book_table: boolean;
  online_order: boolean;
  listed_type: string;
}

const PAGE_SIZE = 1000;

export async function fetchAllRestaurants(): Promise<DBRestaurant[]> {
  const supabase = getSupabase();
  const rows: DBRestaurant[] = [];
  let offset = 0;

  while (true) {
    const { data, error } = await supabase
      .from('restaurants')
      .select('*')
      .range(offset, offset + PAGE_SIZE - 1);

    if (error) throw new Error(`Supabase error: ${error.message}`);
    if (!data || data.length === 0) break;

    rows.push(...(data as DBRestaurant[]));
    if (data.length < PAGE_SIZE) break;
    offset += PAGE_SIZE;
  }

  return rows;
}
