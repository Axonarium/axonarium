import Link from "next/link";

export default function NotFound() {
  return (
    <div className="space-y-3">
      <h1 className="text-3xl font-semibold tracking-tight">Not found</h1>
      <p className="text-muted-foreground">
        Nothing here. <Link href="/explore" className="underline underline-offset-4">Explore the connections</Link> instead.
      </p>
    </div>
  );
}
