// The accessibility budget: no WCAG 2.1 A or AA violation axe-core can find on any page type, and no page that
// throws or meets a server error on the way (ADR 0025).
import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, test } from "@playwright/test";

import { CLAIM, PAGES } from "./pages";

const TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];

async function violations(page: Page): Promise<string[]> {
  const results = await new AxeBuilder({ page }).withTags(TAGS).analyze();
  return results.violations.map(
    (v) => `${v.id} (${v.impact}): ${v.help}; ${v.nodes.length} node(s), e.g. ${v.nodes.slice(0, 3).map((n) => n.target.join(" ")).join(" | ")}`,
  );
}

/** Uncaught errors and server errors while the page loads. */
function failures(page: Page): string[] {
  const found: string[] = [];
  page.on("pageerror", (error) => found.push(`uncaught: ${error.message}`));
  page.on("response", (response) => {
    if (response.status() >= 500) found.push(`HTTP ${response.status()}: ${response.url()}`);
  });
  return found;
}

for (const [name, path] of Object.entries(PAGES)) {
  test(`the ${name} page`, async ({ page }) => {
    const errors = failures(page);
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    expect(errors).toEqual([]);
    expect(await violations(page)).toEqual([]);
  });
}

test("the claim page's evidence form, open", async ({ page }) => {
  const errors = failures(page);
  await page.goto(`/claims/${CLAIM}`);
  const supports = page.getByRole("button", { name: "Supports" });
  test.skip((await supports.count()) === 0, "submissions aren't configured in this build (ADR 0024)");
  await supports.click();
  await page.getByRole("textbox").fill("not an identifier");
  await page.getByRole("textbox").blur();
  expect(errors).toEqual([]);
  expect(await violations(page)).toEqual([]);
});
