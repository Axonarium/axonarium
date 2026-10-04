import type { NextRequest } from "next/server";

import { paging, toConnection } from "@/lib/api";
import { answer, number } from "@/lib/api-route";
import { getRegionNames, listConnections } from "@/lib/data";

export async function GET(request: NextRequest) {
  return answer(async () => {
    const params = request.nextUrl.searchParams;
    const page = paging(params);
    const found = await listConnections({
      subject: params.get("subject"),
      object: params.get("object"),
      species: params.get("species"),
      predicate: params.get("predicate"),
      minDensity: number(params, "min_density"),
      ...page,
    });
    if (!found) return null;
    const names = await getRegionNames([...new Set(found.items.flatMap((e) => [e.subject_id, e.object_id]))]);
    return { items: found.items.map((e) => toConnection(e, names)), ...page, total: found.total };
  });
}
