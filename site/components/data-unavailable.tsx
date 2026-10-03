export function DataUnavailable({ reason }: { reason: string }) {
  return (
    <p role="status" className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
      The data is unavailable right now ({reason}). Everything is also published as files on GitHub.
    </p>
  );
}
