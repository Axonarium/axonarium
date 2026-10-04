import { describe, expect, it } from "vitest";

import { SITE, sitemapUrls } from "./sitemap";

describe("sitemapUrls", () => {
  it("lists the pages, every connection, and every connected atlas region once", () => {
    const urls = sitemapUrls(
      [
        { id: "MBA:295|projects_to|MBA:672|NCBITaxon:10090", subject_id: "MBA:295", object_id: "MBA:672" },
        { id: "MBA:972|projects_to|MBA:295|NCBITaxon:10090", subject_id: "MBA:972", object_id: "MBA:295" },
      ],
      new Set(["MBA:295", "MBA:672", "MBA:972"]),
    );
    expect(urls).toContain(`${SITE}/brain`);
    expect(urls).toContain(`${SITE}/edges/MBA%3A295%7Cprojects_to%7CMBA%3A672%7CNCBITaxon%3A10090`);
    expect(urls.filter((u) => u === `${SITE}/regions/MBA%3A295`)).toHaveLength(1);
    expect(urls).toHaveLength(6 + 2 + 3);
    expect(urls).toContain(`${SITE}/regions`);
  });

  it("leaves out ends that aren't atlas regions", () => {
    const urls = sitemapUrls([{ id: "e", subject_id: "UBERON:0002887", object_id: "MBA:672" }], new Set(["MBA:672"]));
    expect(urls.some((u) => u.includes("UBERON"))).toBe(false);
  });
});
