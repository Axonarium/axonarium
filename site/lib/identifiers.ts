// A submitted paper identifier's canonical source ID (doi:, pubmed:, pmc: or arxiv:), or null if it names none. A port of
// checks/submissions.py's canonical_identifier (ADR 0021): both are tested against checks/tests/identifier_forms.json,
// so the site refuses exactly what triage would. Only the registries' own URLs are understood, never the page behind a
// link; anything else, including other URLs and free text, is refused.

export const MAX_LENGTH = 300;
export const NOT_AN_IDENTIFIER =
  "That isn't a DOI, PubMed ID, PubMed Central ID or arXiv ID, or a link to one on doi.org, PubMed, PubMed Central, " +
  "Europe PMC, arXiv, bioRxiv or medRxiv.";

const DOI = String.raw`(10\.\d{4,9}/[!-~]+)`;
type Scheme = "doi" | "pubmed" | "pmc" | "arxiv";
const FORMS: [string, Scheme][] = [
  [String.raw`(?:doi:\s*)?${DOI}`, "doi"],
  [String.raw`https?://(?:dx\.)?doi\.org/${DOI}`, "doi"],
  [String.raw`https?://(?:www\.)?(?:biorxiv|medrxiv)\.org/content/(10\.1101/(?:\d{4}\.\d{2}\.\d{2}\.)?\d{6,})(?:v\d+)?(?:\.full(?:\.pdf)?|\.abstract)?/?`, "doi"],
  [String.raw`(?:pmid:?\s*)?([1-9]\d{0,8})`, "pubmed"],
  [String.raw`https?://pubmed\.ncbi\.nlm\.nih\.gov/([1-9]\d{0,8})/?`, "pubmed"],
  [String.raw`https?://(?:www\.)?ncbi\.nlm\.nih\.gov/pubmed/([1-9]\d{0,8})/?`, "pubmed"],
  [String.raw`https?://(?:www\.)?europepmc\.org/(?:article|abstract)/MED/([1-9]\d{0,8})/?`, "pubmed"],
  [String.raw`(?:pmcid:?\s*)?(PMC[1-9]\d*)`, "pmc"],
  [String.raw`https?://(?:www\.)?(?:ncbi\.nlm\.nih\.gov/pmc|pmc\.ncbi\.nlm\.nih\.gov)/articles/(PMC[1-9]\d*)/?`, "pmc"],
  [String.raw`https?://(?:www\.)?europepmc\.org/(?:article|abstract)/PMC/(PMC[1-9]\d*)/?`, "pmc"],
  [String.raw`(?:arxiv:\s*)?(\d{4}\.\d{4,5})(?:v[1-9]\d*)?`, "arxiv"],
  [String.raw`https?://(?:www\.)?arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})(?:v[1-9]\d*)?(?:\.pdf)?/?`, "arxiv"],
];
const COMPILED = FORMS.map(([pattern, scheme]) => [new RegExp(`^(?:${pattern})$`, "i"), scheme] as const);

// The exact form each registry is asked for (checks/identifiers.py, CANONICAL).
const CANONICAL: Record<Scheme, RegExp> = {
  doi: /^10\.[0-9]{4,9}\/[!-~]+$/,
  pubmed: /^[1-9][0-9]*$/,
  pmc: /^PMC[1-9][0-9]*$/,
  arxiv: /^[0-9]{4}\.[0-9]{4,5}(v[1-9][0-9]*)?$/,
};

/** Percent-decoding like Python's urllib.parse.unquote: a malformed escape is left as it is, and a byte that isn't valid
 * UTF-8 becomes U+FFFD (so a DOI holding one is refused, as in Python). */
function unquote(text: string): string {
  return text.replace(/(?:%[0-9a-f]{2})+/gi, (run) => {
    try {
      return decodeURIComponent(run);
    } catch {
      return run.replace(/%([0-9a-f]{2})/gi, (_, hex: string) => {
        const byte = parseInt(hex, 16);
        return byte < 0x80 ? String.fromCharCode(byte) : "\ufffd";
      });
    }
  });
}

/** Python's str.strip(): Unicode whitespace from both ends. */
function strip(text: string): string {
  return text.replace(/^[\s\x1c-\x1f\x85]+|[\s\x1c-\x1f\x85]+$/gu, "");
}

export function canonicalIdentifier(raw: unknown): string | null {
  const text = typeof raw === "string" ? strip(raw) : "";
  if (!text || [...text].length > MAX_LENGTH) return null; // code points, as Python counts
  for (const [pattern, scheme] of COMPILED) {
    // Whitespace is allowed only after a label such as "PMID".
    const match = pattern.exec(scheme === "doi" ? unquote(text) : text);
    if (!match) continue;
    const value = match[1];
    const id = { doi: value.toLowerCase(), pubmed: value, pmc: value.toUpperCase(), arxiv: value }[scheme];
    return CANONICAL[scheme].test(id) ? `${scheme}:${id}` : null;
  }
  return null;
}
