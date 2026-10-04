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
