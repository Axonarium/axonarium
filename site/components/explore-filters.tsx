"use client";

// The explore page's filters: a plain GET form, so they work without JavaScript; with it, a change submits at once.

import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import { predicateLabel, speciesName } from "@/lib/format";

const FILTERS = [
  { name: "species", label: "Species", format: speciesName },
  { name: "predicate", label: "Connection", format: predicateLabel },
] as const;

export function ExploreFilters({ facets, chosen }: { facets: Record<"species" | "predicate", string[]>; chosen: Record<"species" | "predicate", string> }) {
  return (
    <form method="get" action="/explore" className="flex flex-wrap items-center gap-4">
      {FILTERS.map(({ name, label, format }) => (
        <label key={name} className="flex items-center gap-2 text-sm">
          <span className="text-muted-foreground">{label}</span>
          <NativeSelect name={name} defaultValue={chosen[name]} onChange={(event) => event.currentTarget.form?.requestSubmit()}>
            <NativeSelectOption value="">All</NativeSelectOption>
            {facets[name].map((value) => (
              <NativeSelectOption key={value} value={value}>
                {format(value)}
              </NativeSelectOption>
            ))}
          </NativeSelect>
        </label>
      ))}
      <noscript>
        <button type="submit" className="rounded-lg border px-2.5 py-1 text-sm">
          Filter
        </button>
      </noscript>
    </form>
  );
}
