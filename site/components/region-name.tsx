import Link from "next/link";

import type { Label } from "@/lib/regions";

/**
 * An entity as its acronym and ID, with its full name: visible in headings, and on hover and for screen readers
 * in tables, where space is short. Atlas regions link to their page; UBERON terms and neuron types have none.
 */
export function RegionName({ label, heading = false }: { label: Label; heading?: boolean }) {
  if (!label.long) return <span className="font-mono">{label.id}</span>;
  const short = label.href ? (
    <Link href={label.href} className="underline-offset-4 hover:underline">
      {label.short}
    </Link>
  ) : (
    <span>{label.short}</span>
  );
  const long = label.long !== label.short ? label.long : null;
  if (heading)
    return (
      <span>
        {short}
        {long && <span className="font-normal text-muted-foreground"> ({long})</span>}
      </span>
    );
  return (
    <span>
      {long ? (
        <abbr title={long} className="no-underline">
          {short}
        </abbr>
      ) : (
        short
      )}
      {long && <span className="sr-only"> ({long})</span>}{" "}
      <span className="font-mono text-xs text-muted-foreground">{label.id}</span>
    </span>
  );
}
