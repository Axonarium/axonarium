// The explore page's state, all in its URL (?species=…&predicate=…&page=…), so every view can be shared and works
// without JavaScript. The server reads it, filters and pages the connections, and renders only the page shown.

export const PAGE_SIZE = 100;

export interface ExploreState {
  species: string;
  predicate: string;
  page: number;
}

type Params = Record<string, string | string[] | undefined>;
const one = (value: string | string[] | undefined) => (typeof value === "string" ? value : "");

/** The URL's filters, kept only when they name a value the connections have; the page, 1 or more. */
export function exploreState(params: Params, facets: { species: string[]; predicate: string[] }): ExploreState {
  const pick = (name: "species" | "predicate") => (facets[name].includes(one(params[name])) ? one(params[name]) : "");
  const page = Number.parseInt(one(params.page), 10);
  return { species: pick("species"), predicate: pick("predicate"), page: Number.isFinite(page) && page > 1 ? page : 1 };
}

export function exploreHref(state: ExploreState): string {
  const query = new URLSearchParams();
  if (state.species) query.set("species", state.species);
  if (state.predicate) query.set("predicate", state.predicate);
  if (state.page > 1) query.set("page", String(state.page));
  const text = query.toString();
  return text ? `/explore?${text}` : "/explore";
}

export const pageCount = (total: number) => Math.max(1, Math.ceil(total / PAGE_SIZE));
