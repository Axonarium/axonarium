import type { Label } from "@/lib/regions";

/** An entity as its acronym (with the full name on hover and for screen readers) and its ID. */
export function RegionName({ label }: { label: Label }) {
  if (!label.long) return <span className="font-mono">{label.id}</span>;
  return (
    <span>
      <abbr title={label.long} className="no-underline">
        {label.short}
      </abbr>
      <span className="sr-only"> ({label.long})</span>{" "}
      <span className="font-mono text-xs text-muted-foreground">{label.id}</span>
    </span>
  );
}
