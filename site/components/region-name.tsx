import type { Label } from "@/lib/regions";

/**
 * An entity as its acronym and ID, with its full name: visible in headings, and on hover and for screen readers
 * in tables, where space is short.
 */
export function RegionName({ label, heading = false }: { label: Label; heading?: boolean }) {
  if (!label.long) return <span className="font-mono">{label.id}</span>;
  if (heading)
    return (
      <span>
        {label.short} <span className="font-normal text-muted-foreground">({label.long})</span>
      </span>
    );
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
