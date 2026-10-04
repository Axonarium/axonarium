import type { NextRequest } from "next/server";

import { toClaim } from "@/lib/api";
import { answer, NotFound } from "@/lib/api-route";
import { getClaim } from "@/lib/data";
import { edgeFromParam } from "@/lib/format";

export async function GET(_request: NextRequest, ctx: RouteContext<"/api/v1/claims/[id]">) {
  return answer(async () => {
    const id = edgeFromParam((await ctx.params).id);
    const claim = await getClaim(id);
    if (claim === null) throw new NotFound(`No claim ${id}`);
    return claim && toClaim(claim);
  });
}
