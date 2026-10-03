"use client"; // Error boundaries must be Client Components

import { Button } from "@/components/ui/button";

export default function Error({ retry }: { error: Error & { digest?: string }; retry: () => void }) {
  return (
    <div role="alert" className="space-y-3">
      <h1 className="text-3xl font-semibold tracking-tight">The data couldn&apos;t be read</h1>
      <p className="text-muted-foreground">
        The database didn&apos;t answer in time. Everything is also published as files on{" "}
        <a href="https://github.com/axonarium/axonarium" className="underline underline-offset-4">
          GitHub
        </a>
        .
      </p>
      <Button variant="outline" onClick={() => retry()}>
        Try again
      </Button>
    </div>
  );
}
