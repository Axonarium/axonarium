import Link from "next/link";

import { DataUnavailable } from "@/components/data-unavailable";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getCounts } from "@/lib/data";

export const revalidate = 300;

const STEPS = [
  ["Claims", "One statement from one paper about one connection in one species, with the figure or table it comes from."],
  ["Checks", "Every identifier and citation is looked up in its registry before anything merges. Retracted papers are flagged."],
  ["Edges", "Connections are computed from claims, never typed by hand, so every line on the map opens its evidence."],
] as const;

export default async function Home() {
  const counts = await getCounts();
  return (
    <div className="space-y-14">
      <section className="space-y-5">
        <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
          An open, cited map of how the brain and body are wired.
        </h1>
        <p className="max-w-2xl text-lg text-muted-foreground">
          Every connection is backed by a cited source, tagged by species and method, and exportable into simulations.
          Axonarium starts with the amygdala of rat, mouse and human, and grows one circuit at a time.
        </p>
        <div className="flex gap-3">
          <Link href="/explore" className={buttonVariants({ size: "lg" })}>
            Explore connections
          </Link>
          <Link href="/about" className={buttonVariants({ size: "lg", variant: "outline" })}>
            How it works
          </Link>
        </div>
      </section>

      <section aria-labelledby="numbers" className="space-y-4">
        <h2 id="numbers" className="text-sm font-medium uppercase tracking-wide text-muted-foreground">
          In the knowledge base today
        </h2>
        {counts ? (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {(
              [
                ["Claims", counts.claims],
                ["Connections", counts.edges],
                ["Sources", counts.sources],
                ["Species", counts.species],
              ] as const
            ).map(([label, value]) => (
              <Card key={label}>
                <CardHeader>
                  <CardDescription>{label}</CardDescription>
                  <CardTitle className="text-3xl tabular-nums">{value.toLocaleString("en")}</CardTitle>
                </CardHeader>
              </Card>
            ))}
          </div>
        ) : (
          <DataUnavailable />
        )}
        {counts && counts.claims === 0 && (
          <p className="text-sm text-muted-foreground">
            The checks, schema and build are in place; the first claims arrive with the atlas and connectivity
            sprints. Follow along on{" "}
            <a href="https://github.com/axonarium/axonarium" className="underline underline-offset-4">
              GitHub
            </a>
            .
          </p>
        )}
      </section>

      <section aria-labelledby="how" className="grid gap-6 sm:grid-cols-3">
        <h2 id="how" className="sr-only">
          How it works
        </h2>
        {STEPS.map(([title, text]) => (
          <Card key={title}>
            <CardHeader>
              <CardTitle>
                <h3>{title}</h3>
              </CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">{text}</CardContent>
          </Card>
        ))}
      </section>
    </div>
  );
}
