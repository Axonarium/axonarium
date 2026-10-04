import { TERMS } from "@/lib/api";
import { answer } from "@/lib/api-route";
import { SITE } from "@/lib/sitemap";

export async function GET() {
  return answer(async () => ({
    name: "Axonarium read API",
    version: "1.0.0",
    openapi: `${SITE}/api/v1/openapi.json`,
    docs: "https://github.com/axonarium/axonarium/blob/main/api/README.md",
    endpoints: ["/regions", "/regions/{id}", "/connections", "/connections/{id}", "/claims/{id}", "/sources/{id}"].map(
      (path) => `${SITE}/api/v1${path}`,
    ),
    terms: Object.values(TERMS),
  }));
}
