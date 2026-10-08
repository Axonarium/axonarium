import Link from "next/link";

/** Previous and next links for a list paged on the server, with the URL of each page. */
export function Pager({ page, pages, href, previous = "← Previous", next = "Next →" }: {
  page: number;
  pages: number;
  href: (page: number) => string;
  previous?: string;
  next?: string;
}) {
  if (pages <= 1) return null;
  return (
    <nav aria-label="Pages" className="flex items-center justify-between gap-4 text-sm">
      {page > 1 ? (
        <Link href={href(page - 1)} className="underline underline-offset-4">
          {previous}
        </Link>
      ) : (
        <span />
      )}
      <span className="text-muted-foreground">
        Page {page} of {pages}
      </span>
      {page < pages ? (
        <Link href={href(page + 1)} className="underline underline-offset-4">
          {next}
        </Link>
      ) : (
        <span />
      )}
    </nav>
  );
}
