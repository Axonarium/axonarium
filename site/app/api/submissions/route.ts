// POST /api/submissions: a visitor's paper for or against a claim (sprint C.3, ADR 0024). Not part of the read API.

import { inboxConfig, inboxDeps } from "@/lib/inbox";
import { clientAddress, handleSubmission } from "@/lib/submit";

const MAX_BODY = 8192; // bytes: a claim ID, a stance, an identifier of at most 300 characters and a token

const reply = (status: number, body: object) =>
  Response.json(body, { status, headers: { "Cache-Control": "no-store" } });

export async function POST(request: Request) {
  const config = inboxConfig();
  if (!config) return reply(503, { status: "closed", message: "Submissions aren't open yet." });
  if (Number(request.headers.get("content-length") ?? 0) > MAX_BODY) {
    return reply(413, { status: "malformed", message: "Too large." });
  }
  const text = await request.text();
  if (new TextEncoder().encode(text).length > MAX_BODY) return reply(413, { status: "malformed", message: "Too large." });
  let body: unknown = null;
  try {
    body = JSON.parse(text);
  } catch {
    // handleSubmission answers a malformed request.
  }
  const outcome = await handleSubmission(body, inboxDeps(config, clientAddress(request.headers)));
  return reply(outcome.status, outcome.body);
}
