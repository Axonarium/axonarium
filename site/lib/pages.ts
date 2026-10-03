// Supabase's REST API returns at most 1,000 rows per request; read everything a page at a time.

export const PAGE = 1000;

export async function fetchAll<T>(page: (from: number, to: number) => Promise<T[]>): Promise<T[]> {
  const all: T[] = [];
  for (let from = 0; ; from += PAGE) {
    const rows = await page(from, from + PAGE - 1);
    all.push(...rows);
    if (rows.length < PAGE) return all;
  }
}
