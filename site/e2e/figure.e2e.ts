// Figure export (sprint 3.5): the brain viewer downloads its 3D and network views as PNGs, and the network view as
// an SVG, each with the citation the data's terms ask for.
import { readFile } from "node:fs/promises";

import { type Download, expect, test } from "@playwright/test";

const contents = async (download: Download) => readFile((await download.path())!);

test("the brain viewer's figures", async ({ page }) => {
  await page.goto("/brain");
  const canvas = page.locator("canvas").first();
  const missing = page.getByText("This build has no brain meshes");
  await expect(canvas.or(missing)).toBeVisible();
  test.skip(await missing.isVisible(), "this build has no meshes (python -m build --meshes)");

  const png = page.getByRole("button", { name: "Download PNG" });
  const svg = page.getByRole("button", { name: "Download SVG" });
  await expect(svg).toBeDisabled(); // SVG comes from the network view only

  const [threeD] = await Promise.all([page.waitForEvent("download"), png.click()]);
  expect(threeD.suggestedFilename()).toMatch(/^axonarium-outputs-all-\d{4}-\d{2}-\d{2}\.png$/);
  const image = await contents(threeD);
  expect(image.subarray(1, 4).toString()).toBe("PNG");
  expect(image.readUInt32BE(16)).toBeGreaterThanOrEqual(2 * 720); // framed, at twice the size

  await page.getByRole("button", { name: "Network", exact: true }).click();
  await expect(svg).toBeEnabled();
  await page.waitForTimeout(1500); // the layout settles
  const [vector] = await Promise.all([page.waitForEvent("download"), svg.click()]);
  expect(vector.suggestedFilename()).toMatch(/\.svg$/);
  const text = (await contents(vector)).toString();
  expect(text).toContain("<svg");
  expect(text).toContain("Allen Mouse Brain Connectivity Atlas");
  expect(text).toMatch(/<circle cx=/);
  expect(text).toMatch(/<path d="M/);

  const [network] = await Promise.all([page.waitForEvent("download"), png.click()]);
  const raster = await contents(network);
  expect(raster.subarray(1, 4).toString()).toBe("PNG");
  expect(raster.readUInt32BE(16)).toBe(2 * 1200); // the SVG at twice the size
});
