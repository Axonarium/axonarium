import Link from "next/link";

import { Citation } from "@/components/citation";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { checkedBy, checkNote, madeBy } from "@/lib/format";
import type { ConnectivityClaim } from "@/lib/types";

/** A claim in a list. `connection` names what it connects, where the list doesn't already say; `cited` is false where
 * the page is its source's own. */
export function ClaimCard({ claim, connection, cited = true }: { claim: ConnectivityClaim; connection?: React.ReactNode; cited?: boolean }) {
  const check = checkedBy(claim);
  const note = claim.verification && claim.verification.verdict !== "agree" ? checkNote(claim) : null;
  return (
    <Card>
      <CardHeader className="flex flex-wrap items-center gap-2">
        <Link href={`/claims/${claim.id}`} className="font-mono underline underline-offset-4">
          {claim.id}
        </Link>
        <Badge variant={claim.result === "present" ? "default" : "secondary"}>{claim.result}</Badge>
        <Badge variant="outline">{claim.evidence_class.replaceAll("_", " ")}</Badge>
        {claim.strength && <Badge variant="outline">strength: {claim.strength}</Badge>}
        {claim.status !== "accepted" && (
          <Badge variant={claim.status === "proposed" ? "outline" : "destructive"}>{claim.status}</Badge>
        )}
      </CardHeader>
      <CardContent className="space-y-2">
        {connection && <p className="font-medium">{connection}</p>}
        <p>{claim.paraphrase}</p>
        {cited ? <Citation cited={claim} locator={claim.locator} /> : <p className="text-sm text-muted-foreground">{claim.locator}</p>}
        <p className="text-sm text-muted-foreground">
          Made by {madeBy(claim)}
          {check ? `; ${check}` : claim.curation.role === "extractor" ? "; not checked yet" : ""}.
          {note && ` “${note}”`}
        </p>
      </CardContent>
    </Card>
  );
}
