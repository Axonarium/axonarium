import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { Citation } from "@/components/citation";
import { DataUnavailable } from "@/components/data-unavailable";
import { Evidence } from "@/components/evidence";
import { RegionName } from "@/components/region-name";
import { getClaim, getRegionNames, getSource } from "@/lib/data";
import { inboxConfig } from "@/lib/inbox";
import { regionLabel } from "@/lib/regions";
import { checkedBy, checkNote, edgeHref, formatMeasurement, madeBy, namesInPaper, predicateLabel, proposedBecause, speciesName } from "@/lib/format";

export const revalidate = 300;

// Rendered on first visit, then cached and revalidated like the other pages (incremental static regeneration).
export async function generateStaticParams() {
  return [];
}

export async function generateMetadata({ params }: PageProps<"/claims/[id]">): Promise<Metadata> {
  return { title: `Claim ${(await params).id}` };
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid gap-1 sm:grid-cols-[12rem_1fr]">
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd>{children}</dd>
    </div>
  );
}

export default async function ClaimPage({ params }: PageProps<"/claims/[id]">) {
  const c = await getClaim((await params).id);
  if (c === undefined) return <DataUnavailable />;
  if (c === null) notFound();
  const [s, regions] = await Promise.all([getSource(c.source_key), getRegionNames([c.subject_id, c.object_id])]);
  const edgeId = [c.subject_id, c.predicate, c.object_id, c.species].join("|");
  const [check, note, called, because] = [checkedBy(c), checkNote(c), namesInPaper(c), proposedBecause(c)];
  // The buttons appear once submissions are open: Turnstile's keys and the Supabase secret key set (ADR 0024).
  const siteKey = inboxConfig() && process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY;
  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <p className="font-mono text-sm text-muted-foreground">{c.id}</p>
        <h1 className="text-3xl font-semibold tracking-tight">
          <RegionName heading label={regionLabel(c.subject_id, regions)} /> {predicateLabel(c.predicate)}{" "}
          <RegionName heading label={regionLabel(c.object_id, regions)} />
        </h1>
        {c.status !== "retracted" && (
          <Link href={edgeHref(edgeId)} className="text-sm underline underline-offset-4">
            All claims for this connection
          </Link>
        )}
      </header>
      {c.status === "retracted" && (
        <p role="note" className="rounded-lg border border-destructive/40 p-4 text-sm">
          This claim is retracted: its source was retracted or the claim was withdrawn. It is kept for the record.
        </p>
      )}
      <dl className="space-y-3">
        <Row label="Species">{speciesName(c.species)}</Row>
        <Row label="Result">{c.result}</Row>
        <Row label="Method">{c.evidence_class.replaceAll("_", " ")}</Row>
        <Row label="Sign">{c.sign}</Row>
        {c.strength && <Row label="Strength">{c.strength}</Row>}
        <Row label="Evidence">{c.paraphrase}</Row>
        {c.excerpt && (
          <Row label="Excerpt">
            <blockquote className="border-l-2 pl-3 italic">{c.excerpt}</blockquote>
          </Row>
        )}
        {c.measurements?.length ? (
          <Row label="Measurements">
            <ul className="space-y-1">
              {c.measurements.map((m, i) => (
                <li key={i} className="tabular-nums">
                  {formatMeasurement(m)}
                </li>
              ))}
            </ul>
          </Row>
        ) : null}
        <Row label="Source">
          <div className="space-y-1">
            {s?.title && <p>{s.title}</p>}
            {s && (s.journal || s.year) && (
              <p className="text-sm text-muted-foreground">{[s.journal, s.year].filter(Boolean).join(", ")}</p>
            )}
            <Citation cited={c} locator={c.locator} />
            {s?.kind === "preprint" && (
              <p className="text-sm text-muted-foreground">A preprint: not yet peer reviewed, so weaker evidence than a published paper.</p>
            )}
            {s?.retracted && <p className="text-sm font-medium text-destructive">This paper has been retracted.</p>}
            {s?.license && <p className="text-sm text-muted-foreground">Licence: {s.license}</p>}
          </div>
        </Row>
        {called && (
          <Row label="Named in the paper">
            “{called[0]}” and “{called[1]}”
          </Row>
        )}
        <Row label="Made by">
          {madeBy(c)}, {c.curation.date}
        </Row>
        {c.verification && check && (
          <Row label="Checked by">
            <div className="space-y-1">
              <p>
                {check}, {c.verification.date}
              </p>
              {note && <p className="text-sm text-muted-foreground">“{note}”</p>}
            </div>
          </Row>
        )}
        <Row label="Status">
          <div className="space-y-1">
            <p>{c.status}</p>
            {because && <p className="text-sm text-muted-foreground">{because}</p>}
          </div>
        </Row>
      </dl>
      {siteKey && c.status !== "retracted" && <Evidence claimId={c.id} siteKey={siteKey} />}
    </div>
  );
}
