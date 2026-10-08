// The path finder (sprint 3.5): a route picked in the brain viewer appears hop by hop with each hop's citations,
// lives in the URL, and passes the accessibility budget (ADR 0025, ADR 0026).
import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("a route through the brain viewer", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.emulateMedia({ reducedMotion: "reduce" }); // every hop at once
  await page.goto("/brain");
  const from = page.locator("#route-from");
  const missing = page.getByText("This build has no brain meshes");
  await expect(from.or(missing)).toBeVisible();
  test.skip(await missing.isVisible(), "this build has no meshes (python -m build --meshes)");

  const start = (await from.locator("option").nth(1).getAttribute("value"))!;
  await from.selectOption(start);
  const to = page.locator("#route-to");
  const end = (await to.locator("option").nth(1).getAttribute("value"))!;
  await to.selectOption(end);

  await expect(page.getByRole("status").filter({ hasText: /^Hop (\d+) of \1:/ })).toBeVisible();
  await expect(page).toHaveURL(new RegExp(`from=${encodeURIComponent(start)}&to=${encodeURIComponent(end)}`));
  const hops = page.locator("aside ol > li");
  expect(await hops.count()).toBeGreaterThan(0);
  await expect(hops.first().getByRole("link", { name: /^(DOI|PubMed|PMC|arXiv)/ }).first()).toBeVisible();
  // Replay is enabled once the last hop shows, then fades from half to full opacity (the button's transition); axe
  // skips disabled buttons but would measure this one mid-fade.
  const replay = page.getByRole("button", { name: "Replay" });
  await expect(replay).toBeEnabled();
  await expect(replay).toHaveCSS("opacity", "1");
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  expect(results.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(" | ")}`)).toEqual([]);

  await page.getByRole("button", { name: "Network", exact: true }).click();
  await page.getByRole("button", { name: "Clear" }).click();
  await expect(page).not.toHaveURL(/from=/);
  await expect(page.getByRole("heading", { name: /connections?, strongest first/ })).toBeVisible();

  // Opened from its URL, the route is drawn again.
  await page.goto(`/brain?from=${encodeURIComponent(start)}&to=${encodeURIComponent(end)}`);
  await expect(page.getByRole("status").filter({ hasText: /^Hop (\d+) of \1:/ })).toBeVisible();
  expect(errors).toEqual([]);
});
