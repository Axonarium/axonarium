// Rows of the serving tables (build/tables.py, ADR 0008).

/** Gap mode (ADR 0027): a connection that is plausible but untested, suggested by the build (build/gaps.py). */
export interface Gap {
  id: string;
  subject_id: string;
  object_id: string;
  atlas: string;
  species: string;
  /** How it was suggested: "neighbours", another subdivision of the same parent projecting there. */
  basis: string;
  /** The strongest projection density among the connections that suggest it. */
  density: number | null;
  /** The IDs of those connections. */
  suggested_by: string[];
}

export interface Edge {
  id: string;
  subject_id: string;
  subject_type: string;
  predicate: string;
  object_id: string;
  object_type: string;
  species: string;
  n_claims: number;
  n_present: number;
  n_absent: number;
  n_ambiguous: number;
  n_disputed: number;
  evidence_classes: string[];
  strength: string | null;
  signs: string[];
  claim_ids: string[];
  /** The strongest projection density among the claims that found the connection. */
  density: number | null;
  /** The reuse terms of its claims (build/terms.py). */
  terms: string[];
}

/** The columns the explore table shows. */
export type EdgeSummary = Pick<
  Edge,
  "id" | "subject_id" | "predicate" | "object_id" | "species" | "n_claims" | "n_present" | "n_absent" | "strength" | "density"
>;

export interface Measurement {
  quantity: string;
  value: number;
  unit: string;
  sd?: number | null;
  sem?: number | null;
  ci_low?: number | null;
  ci_high?: number | null;
  n?: number | null;
}

export interface Curation {
  by: string;
  role: string;
  date: string;
  orcid?: string;
  model?: string;
  prompt?: string;
}

export interface Verification extends Curation {
  verdict: string;
}

export interface ConnectivityClaim {
  id: string;
  subject_type: string;
  subject_id: string;
  subject_atlas: string | null;
  predicate: string;
  object_type: string;
  object_id: string;
  object_atlas: string | null;
  species: string;
  evidence_class: string;
  result: string;
  sign: string;
  strength: string | null;
  measurements: Measurement[] | null;
  source_key: string;
  doi: string | null;
  pmid: string | null;
  pmcid: string | null;
  arxiv: string | null;
  locator: string;
  paraphrase: string;
  excerpt: string | null;
  curation: Curation;
  verification: Verification | null;
  status: string;
  extra: Record<string, unknown> | null;
  /** Under which terms the claim may be reused: "cc-by-4.0" or "allen-institute" (build/terms.py). */
  terms: string;
}

export interface Source {
  id: string;
  title: string | null;
  year: number | null;
  journal: string | null;
  /** journal_article, preprint, dataset or other, from the source's registry; the allowlist decides which a claim may cite. */
  kind: string;
  license: string | null;
  open_access: boolean | null;
  retracted: boolean | null;
}

export interface Counts {
  claims: number;
  edges: number;
  sources: number;
  species: number;
}

export interface Atlas {
  id: string;
  name: string;
  species: string;
  version: string;
  url: string | null;
  brainglobe_name: string | null;
  citation: string | null;
}
