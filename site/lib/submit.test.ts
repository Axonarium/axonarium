import { describe, expect, it } from "vitest";

import { NOT_AN_IDENTIFIER } from "./identifiers";
import { clientAddress, clientHash, handleSubmission, type Inserted, type SubmitDeps } from "./submit";
import { verifyTurnstile } from "./turnstile";

const CLAIM = "clm-pq22bk4dtz";
const valid = { claim: CLAIM, stance: "supports", identifier: " https://doi.org/10.1038/S41467-021-22915-5 ", token: "t" };

function deps(overrides: Partial<SubmitDeps> = {}) {
  const calls: string[] = [];
  const base: SubmitDeps = {
    verify: async (token) => (calls.push(`verify ${token}`), token === "t"),
    claimStatus: async (id) => (calls.push(`claim ${id}`), id === CLAIM ? "accepted" : null),
    insert: async (claim, stance, identifier): Promise<Inserted> => (
      calls.push(`insert ${claim} ${stance} ${identifier}`), { status: "received", id: "u1" }
    ),
  };
  return { deps: { ...base, ...overrides }, calls };
}

describe("handleSubmission", () => {
  it("checks everything, then inserts the identifier as submitted", async () => {
    const { deps: d, calls } = deps();
    expect(await handleSubmission(valid, d)).toEqual({
      status: 201,
      body: { status: "received", message: "Thank you. The paper is in the triage queue.", id: "u1" },
    });
    expect(calls).toEqual([
      "verify t",
      `claim ${CLAIM}`,
      `insert ${CLAIM} supports https://doi.org/10.1038/S41467-021-22915-5`,
    ]);
  });

  it.each([
    [null],
    ["text"],
    [{ ...valid, claim: "hom-pq22bk4dtz" }],
    [{ ...valid, claim: "clm-1" }],
    [{ ...valid, stance: "endorses" }],
    [{ ...valid, identifier: 42 }],
    [{ ...valid, token: undefined }],
    [{ ...valid, token: "x".repeat(2049) }],
  ])("refuses a malformed request, before anything is called: %j", async (body) => {
    const { deps: d, calls } = deps();
    expect((await handleSubmission(body, d)).status).toBe(400);
    expect(calls).toEqual([]);
  });

  it("refuses anything but an identifier before spending the visitor's token", async () => {
    const { deps: d, calls } = deps();
    const outcome = await handleSubmission({ ...valid, identifier: "https://bit.ly/3xyz" }, d);
    expect(outcome).toEqual({ status: 422, body: { status: "not-an-identifier", message: NOT_AN_IDENTIFIER } });
    expect(calls).toEqual([]);
  });

  it("blocks a scripted submission whose bot check fails, before touching the data", async () => {
    const { deps: d, calls } = deps();
    expect((await handleSubmission({ ...valid, token: "forged" }, d)).status).toBe(403);
    expect(calls).toEqual(["verify forged"]);
  });

  it("answers an unknown, a retracted and an unreachable claim", async () => {
    expect((await handleSubmission({ ...valid, claim: "clm-0000000000" }, deps().deps)).status).toBe(404);
    expect((await handleSubmission(valid, deps({ claimStatus: async () => "retracted" }).deps)).status).toBe(409);
    expect((await handleSubmission(valid, deps({ claimStatus: async () => undefined }).deps)).status).toBe(503);
  });

  it("passes on the database's rate limits, and its failures", async () => {
    const limited = deps({ insert: async () => ({ status: "rate-limited" }) }).deps;
    expect(await handleSubmission(valid, limited)).toMatchObject({ status: 429, body: { status: "rate-limited" } });
    const busy = deps({ insert: async () => ({ status: "busy" }) }).deps;
    expect(await handleSubmission(valid, busy)).toMatchObject({ status: 429, body: { status: "busy" } });
    const down = deps({ insert: async () => Promise.reject(new Error("down")) }).deps;
    expect(await handleSubmission(valid, down)).toMatchObject({ status: 503, body: { status: "unavailable" } });
  });
});

describe("the submitter", () => {
  it("is the address Vercel reports", () => {
    expect(clientAddress(new Headers({ "x-real-ip": "203.0.113.7", "x-forwarded-for": "198.51.100.1" }))).toBe("203.0.113.7");
    expect(clientAddress(new Headers({ "x-forwarded-for": "198.51.100.1, 10.0.0.1" }))).toBe("198.51.100.1");
    expect(clientAddress(new Headers())).toBeNull();
  });

  it("is counted by a keyed hash, never the address", () => {
    const hash = clientHash("203.0.113.7", "key");
    expect(hash).toMatch(/^[0-9a-f]{32}$/);
    expect(hash).toBe(clientHash("203.0.113.7", "key"));
    expect(hash).not.toBe(clientHash("203.0.113.7", "other key"));
    expect(clientHash(null, "key")).toBe(clientHash(null, "key"));
  });
});

describe("verifyTurnstile", () => {
  const answering = (status: number, body: unknown, seen: RequestInit[] = []) =>
    (async (_url: string, init: RequestInit) => (seen.push(init), new Response(JSON.stringify(body), { status }))) as typeof fetch;

  it("asks Cloudflare with the secret, the token and the address", async () => {
    const seen: RequestInit[] = [];
    expect(await verifyTurnstile("tok", "sec", "203.0.113.7", answering(200, { success: true, action: "submit-evidence" }, seen))).toBe(true);
    expect(Object.fromEntries(seen[0].body as URLSearchParams)).toEqual({ secret: "sec", response: "tok", remoteip: "203.0.113.7" });
  });

  it("accepts Cloudflare's test keys, which answer without an action", async () => {
    expect(await verifyTurnstile("tok", "sec", null, answering(200, { success: true }))).toBe(true);
  });

  it.each([
    ["a refusal", answering(200, { success: false, "error-codes": ["invalid-input-response"] })],
    ["another form's token", answering(200, { success: true, action: "login" })],
    ["an error", answering(500, {})],
    ["no answer", (async () => Promise.reject(new Error("timeout"))) as unknown as typeof fetch],
  ])("fails closed on %s", async (_name, fetcher) => {
    expect(await verifyTurnstile("tok", "sec", null, fetcher)).toBe(false);
  });

  it("never asks about an empty or oversized token", async () => {
    const seen: RequestInit[] = [];
    expect(await verifyTurnstile("", "sec", null, answering(200, { success: true }, seen))).toBe(false);
    expect(await verifyTurnstile("x".repeat(2049), "sec", null, answering(200, { success: true }, seen))).toBe(false);
    expect(seen).toEqual([]);
  });
});
