import { citationLinks, type Cited } from "@/lib/format";

export function Citation({ cited, locator }: { cited: Cited; locator?: string | null }) {
  return (
    <span className="text-sm">
      {citationLinks(cited).map((link, i) => (
        <span key={link.href}>
          {i > 0 && " · "}
          <a href={link.href} className="underline underline-offset-4 hover:text-foreground">
            {link.label}
          </a>
        </span>
      ))}
      {locator && <span className="text-muted-foreground">, {locator}</span>}
    </span>
  );
}
