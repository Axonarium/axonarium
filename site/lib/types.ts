// Rows of the serving tables (build/tables.py, ADR 0008).

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
}

export interface Source {
  id: string;
  title: string | null;
  year: number | null;
  journal: string | null;
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
