// Pure helpers for showing records: labels, citation links and URL segments.

const SPECIES: Record<string, string> = {
  "NCBITaxon:10090": "Mouse",
  "NCBITaxon:10116": "Rat",
  "NCBITaxon:9606": "Human",
};

export function speciesName(curie: string): string {
  return SPECIES[curie] ?? curie;
}

export function predicateLabel(predicate: string): string {
  return predicate.replaceAll("_", " ");
}

export interface Cited {
  doi?: string | null;
  pmid?: string | null;
  pmcid?: string | null;
  arxiv?: string | null;
}

export interface Link {
  label: string;
  href: string;
}

/** A link for every identifier a citation carries, DOI first. */
export function citationLinks(cited: Cited): Link[] {
  const links: Link[] = [];
  if (cited.doi) {
    const path = cited.doi.split("/").map(encodeURIComponent).join("/");
    links.push({ label: `DOI ${cited.doi}`, href: `https://doi.org/${path}` });
  }
  if (cited.pmid) links.push({ label: `PubMed ${cited.pmid}`, href: `https://pubmed.ncbi.nlm.nih.gov/${cited.pmid}/` });
  if (cited.pmcid) links.push({ label: cited.pmcid, href: `https://pmc.ncbi.nlm.nih.gov/articles/${cited.pmcid}/` });
  if (cited.arxiv) links.push({ label: `arXiv ${cited.arxiv}`, href: `https://arxiv.org/abs/${cited.arxiv}` });
  return links;
}

/** The page of an edge; its ID ("subject|predicate|object|species") becomes one URL segment. */
export function edgeHref(id: string): string {
  return `/edges/${encodeURIComponent(id)}`;
}

/** Sort order for connections: the strongest projection density first, those without one last, then by ID. */
export function strongestFirst(a: { id: string; density: number | null }, b: { id: string; density: number | null }): number {
  return (b.density ?? -1) - (a.density ?? -1) || a.id.localeCompare(b.id);
}

/** The page of an atlas region. */
export function regionHref(id: string): string {
  return `/regions/${encodeURIComponent(id)}`;
}

/** An edge or region ID from its URL segment, whether or not the framework has already decoded it. */
export function edgeFromParam(segment: string): string {
  return segment.includes("%") ? decodeURIComponent(segment) : segment;
}

export interface MeasurementLike {
  quantity: string;
  value: number;
  unit: string;
  sd?: number | null;
  sem?: number | null;
  ci_low?: number | null;
  ci_high?: number | null;
  n?: number | null;
}

/** One measurement as text, with whatever uncertainty it reports ("1" is the unit of dimensionless quantities). */
export function formatMeasurement(m: MeasurementLike): string {
  const uncertainty = [
    m.sd != null && `SD ${m.sd}`,
    m.sem != null && `SEM ${m.sem}`,
    m.ci_low != null && m.ci_high != null && `CI ${m.ci_low}–${m.ci_high}`,
  ].filter(Boolean);
  const unit = m.unit === "1" ? "" : ` ${m.unit}`;
  return (
    `${m.quantity.replaceAll("_", " ")}: ${m.value}${unit}` +
    (uncertainty.length ? ` (${uncertainty.join("; ")})` : "") +
    (m.n != null ? `, n = ${m.n}` : "")
  );
}

/** The URL of a page with one search parameter set (or removed, when the value is empty), keeping the others. */
export function withParam(pathname: string, params: URLSearchParams, name: string, value: string): string {
  const next = new URLSearchParams(params);
  if (value) next.set(name, value);
  else next.delete(name);
  const query = next.toString();
  return query ? `${pathname}?${query}` : pathname;
}

/** An atlas citation ("Authors year, https://…") as its text and its link, if it has one. */
export function citationParts(citation: string): { text: string; href: string | null } {
  const match = citation.match(/^(.*?)[,;]?\s*(https?:\/\/\S+)\s*$/);
  return match ? { text: match[1].trim(), href: match[2] } : { text: citation, href: null };
}

/** The fields that say who made a claim and who checked it. */
export interface Provenanced {
  curation: { by: string; role: string; model?: string; prompt?: string; orcid?: string };
  verification?: { by: string; model?: string; verdict: string } | null;
  status: string;
  extra?: Record<string, unknown> | null;
}

const VERDICTS: Record<string, string> = { agree: "agrees", disagree: "disagrees", unsure: "is unsure" };

/** Who made a claim: a person, an AI model reading the paper (ADR 0028), or an adapter reading a database. */
export function madeBy(c: Provenanced): string {
  const { by, role, model, prompt, orcid } = c.curation;
  if (by === "human") return orcid ? `a curator (ORCID ${orcid})` : "a curator";
  if (role === "extractor") return `an AI model reading the paper (${[model, prompt].filter(Boolean).join(", ")})`;
  if (role === "ingester") return `an adapter reading a database (${prompt ?? model})`;
  return `an agent (${model})`;
}

/** What the independent check said, or null when nothing has checked the claim yet. */
export function checkedBy(c: Provenanced): string | null {
  const v = c.verification;
  if (!v) return null;
  return `${v.by === "human" ? "a curator" : `a second AI model (${v.model})`} ${VERDICTS[v.verdict] ?? v.verdict}`;
}

/** The checker's one-sentence reason, when it gave one. */
export function checkNote(c: Provenanced): string | null {
  const note = c.extra?.["verify.note"];
  return typeof note === "string" && note ? note : null;
}

/** The names a paper used for the claim's two ends, when an extractor recorded them. */
export function namesInPaper(c: Provenanced): [string, string] | null {
  const [subject, object] = [c.extra?.["extract.subject_name"], c.extra?.["extract.object_name"]];
  return typeof subject === "string" && typeof object === "string" && subject && object ? [subject, object] : null;
}

/** Why a claim is proposed rather than accepted, by how it was made. */
export function proposedBecause(c: Provenanced): string | null {
  if (c.status !== "proposed") return null;
  if (c.curation.role === "extractor")
    return "Drafted and checked by AI models; it stays proposed until people have audited a sample of such claims.";
  if (c.extra && "allen.experiment" in c.extra) return "Most of the injected tracer landed outside the region it names.";
  return "Not yet accepted.";
}

/** A source's page on this site. */
export function sourceHref(id: string): string {
  return `/sources/${encodeURIComponent(id)}`;
}

/** The identifier a source's key holds (`doi:…`, `pubmed:…`, `pmc:…` or `arxiv:…`), for its citation links. */
export function citedAs(key: string): Cited {
  const at = key.indexOf(":");
  const [kind, value] = [key.slice(0, at), key.slice(at + 1)];
  if (!value) return {};
  return kind === "doi" ? { doi: value } : kind === "pubmed" ? { pmid: value } : kind === "pmc" ? { pmcid: value } : kind === "arxiv" ? { arxiv: value } : {};
}

/** The page number in a URL's `page` parameter: 1 or more. */
export function pageParam(value: string | string[] | undefined): number {
  const n = Number.parseInt(typeof value === "string" ? value : "", 10);
  return Number.isFinite(n) && n > 1 ? n : 1;
}
