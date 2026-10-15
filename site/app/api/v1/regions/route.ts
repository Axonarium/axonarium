import type { NextRequest } from "next/server";

import { paging, toRegion } from "@/lib/api";
import { answer, flag, moduleId } from "@/lib/api-route";
import { listRegions } from "@/lib/data";

export async function GET(request: NextRequest) {
  return answer(async () => {
    const params = request.nextUrl.searchParams;
    const page = paging(params);
    const found = await listRegions({
      q: params.get("q"),
      atlas: params.get("atlas"),
      amygdala: flag(params, "amygdala"),
      module: moduleId(params),
      ...page,
    });
    return found && { items: found.items.map(toRegion), ...page, total: found.total };
  });
}
