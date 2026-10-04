import Link from "next/link";

import { regionHref } from "@/lib/format";
import type { Label } from "@/lib/regions";

/**
 * An entity as its acronym and ID, with its full name: visible in headings, and on hover and for screen readers
 * in tables, where space is short. Atlas regions link to their page.
 */
export function RegionName({ label, heading = false }: { label: Label; heading?: boolean }) {
  if (!label.long) return <span className="font-mono">{label.id}</span>;
  const short = (
    <Link href={regionHref(label.id)} className="underline-offset-4 hover:underline">
      {label.short}
    </Link>
  );
  if (heading)
    return (
      <span>
        {short} <span className="font-normal text-muted-foreground">({label.long})</span>
      </span>
    );
  return (
    <span>
      <abbr title={label.long} className="no-underline">
        {short}
      </abbr>
      <span className="sr-only"> ({label.long})</span>{" "}
      <span className="font-mono text-xs text-muted-foreground">{label.id}</span>
    </span>
  );
}
