import type { NextRequest } from "next/server";

import { toSource } from "@/lib/api";
import { answer, NotFound } from "@/lib/api-route";
import { getSource } from "@/lib/data";
import { edgeFromParam } from "@/lib/format";

export async function GET(_request: NextRequest, ctx: RouteContext<"/api/v1/sources/[id]">) {
  return answer(async () => {
    const id = edgeFromParam((await ctx.params).id);
    const source = await getSource(id);
    if (source === null) throw new NotFound(`No source ${id}`);
    return toSource(source);
  });
}
