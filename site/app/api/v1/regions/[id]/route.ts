import type { NextRequest } from "next/server";

import { regionDetail } from "@/lib/api";
import { answer, NotFound } from "@/lib/api-route";
import { getRegion } from "@/lib/data";
import { edgeFromParam } from "@/lib/format";

export async function GET(_request: NextRequest, ctx: RouteContext<"/api/v1/regions/[id]">) {
  return answer(async () => {
    const id = edgeFromParam((await ctx.params).id);
    const found = await getRegion(id);
    if (found === null) throw new NotFound(`No atlas region ${id}`);
    return found && regionDetail(found);
  });
}
