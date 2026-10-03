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

/** The edge ID from its URL segment, whether or not the framework has already decoded it. */
export function edgeFromParam(segment: string): string {
  return segment.includes("%") ? decodeURIComponent(segment) : segment;
}
