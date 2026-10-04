---
status: accepted
date: 2026-10-04
decision-makers: Tyler Banks
consulted: Claude (sprint C.3)
---

# Evidence buttons: Turnstile on the server, rate limits in the database

## Context and Problem Statement

The plan lets a visitor send one paper identifier as evidence for or against a claim, with Supports and Contradicts buttons, "protected by Cloudflare Turnstile and rate limits" (Part 3.3). ADR 0021 closed the inbox to Supabase's public API, so that only the site's server, after its checks, can write to it. Sprint C.3 is done when anonymous submission works on a phone and scripted bot submissions are blocked in testing. Where do Turnstile and the rate limits run, and what do the buttons send?

## Considered Options

* Rate limits in a Postgres function the server calls, keyed by a hash of the submitter's address
* A rate-limiting service (Upstash Redis, or Vercel's firewall rules)
* Limits kept in each server instance's memory

## Decision Outcome

Chosen option: "rate limits in a Postgres function", because the inbox is already in Postgres. Counting and inserting in one transaction can't race, and it needs no new service or account. In-memory limits don't hold across Vercel's serverless instances. A rate-limiting service would add an account, a secret and a vendor for a few counts.

* **The buttons** (`site/components/evidence.tsx`): on each claim page that isn't retracted. Each opens one field for an identifier, the Turnstile widget and Send. Nothing else can be sent. The field checks the identifier as it is typed, with the same canonicaliser the server uses. Turnstile's script loads only once the form opens, so reading a claim never contacts Cloudflare. Touch targets are 44 px and the field's text is 16 px, so phones don't zoom.
* **The route** (`POST /api/submissions`; `site/lib/submit.ts`): it refuses a malformed request (400), then an identifier the canonicaliser can't read (422), before Turnstile, so a typo doesn't spend the visitor's token. Then:
  * The token goes to Cloudflare's siteverify with the secret key and the visitor's address. The check fails closed on any error or timeout (403), and refuses a token issued for another action.
  * The claim must exist (404) and not be retracted (409).
  * The submission goes to `submit_evidence()` with the Supabase secret key, as ADR 0021 decided.
* **The canonicaliser** (`site/lib/identifiers.ts`): a TypeScript port of `checks/submissions.py`'s. Both are tested against the same cases (`checks/tests/identifier_forms.json`), so the site refuses exactly what triage would. As ADR 0021 says, existence, retraction and the allowlist are triage's checks (C.4).
* **Rate limits** (`submit_evidence()`, migration `c2929d641286`):
  * Each submitter may send 5 an hour and 20 a day; everyone together, 500 a day.
  * A submitter is a keyed hash (HMAC-SHA256, keyed with the Turnstile secret) of the address Vercel reports, never the address itself.
  * Hashes older than a day are cleared on every call.
  * A per-submitter advisory lock stops two quick requests from both slipping under a limit.
  * Only `service_role`, the secret key, may execute the function. Postgres and Supabase let everyone execute new functions, and Supabase exposes public functions through its API, so every other role loses EXECUTE.
* **Switched on by configuration:** the buttons appear, and the route answers, only once three keys are set: `NEXT_PUBLIC_TURNSTILE_SITE_KEY` (a GitHub variable for the deploy's build), and `TURNSTILE_SECRET_KEY` and `SUPABASE_SECRET_KEY` (Vercel's production settings, server-side only). Until then the route answers 503.

### Consequences

* Good, because every row passes Turnstile and the limits, and the limits hold however many server instances run.
* Good, because the address is never stored, and its hash is gone within a day.
* Good, because the canonicaliser can't drift between the site and triage without a test failing.
* Bad, because the secret key still bypasses row-level security on every table (ADR 0021). A dedicated role remains the stricter option.
* Bad, because many people behind one address, such as a university's, share one submitter's limits. Twenty a day is generous for evidence about one map.
* Neutral: the limits are in a migration, so changing them is a reviewed change.

### Confirmation

* `site/lib/submit.test.ts`: a request with a forged token is refused before any data is touched, and the order of checks holds.
* `build/tests/test_database.py`: the limits, the hash clearing, the function's privileges.
* `site/lib/identifiers.test.ts`: the shared canonicaliser cases.
* Before merging, the form was driven at iPhone 13 size against a production build, with a stand-in Turnstile widget, because the sandbox can't reach Cloudflare. A real submission needs the keys.
