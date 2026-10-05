// Gap mode (sprint 3.5, ADR 0027): the brain viewer lists untested connections its neighbours suggest, each linked to
// a connection that suggests it, and passes the accessibility budget (ADR 0025).
import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("gap mode in the brain viewer", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/brain");
  const canvas = page.locator("canvas").first();
  const missing = page.getByText("This build has no brain meshes");
  await expect(canvas.or(missing)).toBeVisible();
  test.skip(await missing.isVisible(), "this build has no meshes (python -m build --meshes)");
  const gaps = page.getByRole("button", { name: "Untested (gap mode)" });
  test.skip((await gaps.count()) === 0, "this build's data suggests no gaps");

  await gaps.click();
  await expect(page.getByRole("heading", { name: /untested connections?, best suggested first/ })).toBeVisible();
  await expect(page.getByRole("group", { name: "Direction" })).toHaveCount(0); // gaps are outputs only
  const via = page.getByRole("link", { name: /^via / }).first();
  await expect(via).toHaveAttribute("href", /^\/edges\//);
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  expect(results.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(" | ")}`)).toEqual([]);

  // The suggesting connection's page exists.
  const href = (await via.getAttribute("href"))!;
  expect((await page.request.get(href)).status()).toBe(200);

  await page.getByRole("button", { name: "Connections" }).click();
  await expect(page.getByRole("heading", { name: /connections?, strongest first/ })).toBeVisible();
  expect(errors).toEqual([]);
});
