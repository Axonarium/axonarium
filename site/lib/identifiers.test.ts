import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { canonicalIdentifier } from "./identifiers";

// The cases checks/tests/test_submissions.py runs against the Python canonicaliser.
const forms: { canonical: [string, string][]; malformed: string[] } = JSON.parse(
  readFileSync(join(__dirname, "../../checks/tests/identifier_forms.json"), "utf-8"),
);

describe("canonicalIdentifier", () => {
  it.each(forms.canonical)("turns %j into %s", (raw, expected) => {
    expect(canonicalIdentifier(raw)).toBe(expected);
  });

  it.each(forms.malformed.map((raw) => [raw]))("refuses %j", (raw) => {
    expect(canonicalIdentifier(raw)).toBeNull();
  });

  it("refuses anything but a string, and malformed escapes", () => {
    expect(canonicalIdentifier(undefined)).toBeNull();
    expect(canonicalIdentifier(34001873)).toBeNull();
    expect(canonicalIdentifier("https://doi.org/10.1038/abc%ZZ")).toBe("doi:10.1038/abc%zz"); // as Python
    expect(canonicalIdentifier("https://doi.org/10.1038/abc%E2")).toBeNull();
  });
});
