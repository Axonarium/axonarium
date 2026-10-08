import Link from "next/link";

import { Citation } from "@/components/citation";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { checkedBy, checkNote, madeBy } from "@/lib/format";
import type { ConnectivityClaim } from "@/lib/types";

export function ClaimCard({ claim }: { claim: ConnectivityClaim }) {
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
        <p>{claim.paraphrase}</p>
        <Citation cited={claim} locator={claim.locator} />
        <p className="text-sm text-muted-foreground">
          Made by {madeBy(claim)}
          {check ? `; ${check}` : claim.curation.role === "extractor" ? "; not checked yet" : ""}.
          {note && ` “${note}”`}
        </p>
      </CardContent>
    </Card>
  );
}
