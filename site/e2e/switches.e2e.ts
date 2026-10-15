// The brain viewer's switches (ADR 0034): a circuit at a time in the mouse, and the rat's network, both kept in the
// URL, and both passing the accessibility budget (ADR 0025).
import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, test } from "@playwright/test";

async function violations(page: Page): Promise<string[]> {
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  return results.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(" | ")}`);
}

test("the brain viewer switches circuit and species", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/brain");
  await expect(page.getByRole("navigation", { name: "Species" })).toBeVisible();
  const circuits = page.getByRole("group", { name: "Circuit" });
  test.skip((await circuits.count()) === 0, "this build's snapshot has no modules");

  await circuits.getByRole("button", { name: "Hippocampal formation" }).click();
  await expect(page).toHaveURL(/[?&]module=hippocampus/);
  await expect(circuits.getByRole("button", { name: "Hippocampal formation" })).toHaveAttribute("aria-pressed", "true");
  // The mouse's panel comes with its meshes, which builds without `--meshes` lack.
  const missing = page.getByText("This build has no brain meshes");
  const heading = page.getByRole("heading", { name: "Hippocampal formation region" });
  await expect(heading.or(missing)).toBeVisible();
  expect(await violations(page)).toEqual([]);

  // The species switch keeps the circuit.
  await page.getByRole("navigation", { name: "Species" }).getByRole("link", { name: "Rat" }).click();
  await expect(page).toHaveURL(/\/brain\/rat\?module=hippocampus/);
  await expect(page.getByRole("link", { name: "Rat" })).toHaveAttribute("aria-current", "page");
  await expect(page.getByRole("heading", { name: "Hippocampal formation region" })).toBeVisible();
  await expect(page.getByRole("group", { name: "View" })).toHaveCount(0); // no 3D for the rat yet
  expect(await violations(page)).toEqual([]);

  // The first circuit needs no parameter.
  await page.getByRole("group", { name: "Circuit" }).getByRole("button", { name: "Amygdala" }).click();
  await expect(page).not.toHaveURL(/module=/);
  await expect(page.getByRole("heading", { name: /connections?, strongest first/ })).toBeVisible();
  expect(errors).toEqual([]);
});
