// A visitor's evidence for or against a claim (sprint C.3, ADR 0024): checked here, then handed to the database's
// submit_evidence(), which applies the rate limits. Pure, with its dependencies passed in, so tests need no network.

import { createHmac } from "node:crypto";

import { canonicalIdentifier, MAX_LENGTH, NOT_AN_IDENTIFIER } from "./identifiers";
import { MAX_TOKEN } from "./turnstile";

export const STANCES = ["supports", "contradicts"] as const;
export type Stance = (typeof STANCES)[number];
const CLAIM = /^clm-[0-9a-hjkmnp-tv-z]{10}$/;

export type Inserted = { status: "received"; id: string } | { status: "rate-limited" } | { status: "busy" };

export interface SubmitDeps {
  verify(token: string): Promise<boolean>;
  /** The claim's status, null if there is no such claim, undefined if the data can't be reached. */
  claimStatus(id: string): Promise<string | null | undefined>;
  insert(claim: string, stance: Stance, identifier: string): Promise<Inserted>;
}

export interface Outcome {
  status: number;
  body: { status: string; message: string; id?: string };
}

const outcome = (status: number, code: string, message: string, id?: string): Outcome => ({
  status,
  body: id ? { status: code, message, id } : { status: code, message },
});

export async function handleSubmission(body: unknown, deps: SubmitDeps): Promise<Outcome> {
  const { claim, stance, identifier, token } = (typeof body === "object" && body !== null ? body : {}) as Record<string, unknown>;
  if (
    typeof claim !== "string" ||
    !CLAIM.test(claim) ||
    !STANCES.includes(stance as Stance) ||
    typeof identifier !== "string" ||
    identifier.length > MAX_LENGTH * 4 ||
    typeof token !== "string" ||
    token.length > MAX_TOKEN
  ) {
    return outcome(400, "malformed", "The request needs a claim, a stance, an identifier and a Turnstile token.");
  }
  // Checked before Turnstile, so a typo doesn't spend the visitor's token.
  if (canonicalIdentifier(identifier) === null) return outcome(422, "not-an-identifier", NOT_AN_IDENTIFIER);
  if (!(await deps.verify(token))) {
    return outcome(403, "challenge-failed", "The bot check didn't pass. Please try again.");
  }
  const status = await deps.claimStatus(claim);
  if (status === undefined) return outcome(503, "unavailable", "Submissions are unavailable just now. Please try later.");
  if (status === null) return outcome(404, "unknown-claim", "There is no such claim.");
  if (status === "retracted") return outcome(409, "retracted-claim", "This claim is retracted, so it takes no new evidence.");
  let inserted: Inserted;
  try {
    inserted = await deps.insert(claim, stance as Stance, identifier.trim());
  } catch {
    return outcome(503, "unavailable", "Submissions are unavailable just now. Please try later.");
  }
  if (inserted.status === "rate-limited") {
    return outcome(429, "rate-limited", "You've sent several papers recently. Please try again later.");
  }
  if (inserted.status === "busy") {
    return outcome(429, "busy", "Many papers have been sent today. Please try again tomorrow.");
  }
  return outcome(201, "received", "Thank you. The paper is in the triage queue.", inserted.id);
}

/** The submitter's address as Vercel reports it (Vercel overwrites what the client sends), or null. */
export function clientAddress(headers: Headers): string | null {
  return headers.get("x-real-ip") ?? headers.get("x-forwarded-for")?.split(",")[0]?.trim() ?? null;
}

/** A keyed hash of the address, so the database can count submissions without holding the address itself. */
export function clientHash(address: string | null, key: string): string {
  return createHmac("sha256", key).update(address ?? "unknown").digest("hex").slice(0, 32);
}
