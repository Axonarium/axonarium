import type { NextRequest } from "next/server";

import { toClaim, toConnection } from "@/lib/api";
import { answer, NotFound } from "@/lib/api-route";
import { getClaims, getEdge, getRegionNames } from "@/lib/data";
import { edgeFromParam } from "@/lib/format";

export async function GET(_request: NextRequest, ctx: RouteContext<"/api/v1/connections/[id]">) {
  return answer(async () => {
    const id = edgeFromParam((await ctx.params).id);
    const edge = await getEdge(id);
    if (edge === undefined) return null;
    if (edge === null) throw new NotFound(`No connection ${id}`);
    const [claims, names] = await Promise.all([getClaims(edge.claim_ids), getRegionNames([edge.subject_id, edge.object_id])]);
    return { ...toConnection(edge, names), claims_detail: claims.map(toClaim) };
  });
}
