import { answer } from "@/lib/api-route";
import { openapi } from "@/lib/openapi";

export async function GET() {
  return answer(async () => openapi);
}
