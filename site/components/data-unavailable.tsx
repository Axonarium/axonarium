export function DataUnavailable() {
  return (
    <p role="status" className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
      This build isn&apos;t connected to the database. Everything is also published as files on GitHub.
    </p>
  );
}
