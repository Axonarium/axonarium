---
status: accepted
date: 2026-10-04
decision-makers: Tyler Banks
consulted: Claude (sprint C.1)
---

# The community inbox: closed to the public API, and identifiers vetted before use

## Context and Problem Statement

Visitors will be able to submit one paper identifier as evidence for or against a claim, with no free text and no account (plan Part 3.3). Sprint C.1 asks for the inbox those submissions land in, with insert-only row-level security, and for an identifier canonicaliser with Crossref and PubMed checks that rejects malformed, unknown and retracted identifiers. The plan has anonymous visitors inserting rows directly. The same plan protects submissions with Cloudflare Turnstile and rate limits (sprint C.3). How do the inbox and the canonicaliser work, so the later sprints (C.3 the buttons, C.4 triage) can build on them?

## Considered Options

* An inbox closed to Supabase's public API roles, written only by the site's server after Turnstile and rate limits
* The plan's design: public insert-only access for the anonymous role, under row-level security
* No table yet; decide with sprint C.3

## Decision Outcome

Chosen option: "an inbox closed to the public API roles". With public insert access, anyone holding the site's public key, which is public by design, could insert rows straight through Supabase's API. That skips Turnstile and the rate limits, so one script could fill the inbox. Closing the table, and letting only the site's server write to it after its checks, keeps every defence in front of every row.

* **Table** `submissions` (`build/tables.py`, migration `f9f29254abbb`):
  * columns: the claim ID, the stance (`supports` or `contradicts`), the identifier as submitted (1–300 characters) and the time;
  * triage's columns: `status` (`received`, then `closed`), the canonical `source_id`, the closing `reason` and the time it closed;
  * check constraints refuse a malformed claim ID, stance or identifier, whoever writes.
* **Access:** row-level security with no policy for `anon` or `authenticated`, and every privilege revoked from them. The site's server (sprint C.3) inserts with the Supabase secret key, kept server-side, after Turnstile, rate limits and a syntactic check of the identifier. Triage (sprint C.4) reads and closes rows the same way. Submitters follow their own submission through a tracking page served by the site (C.4), never through the table.
* **Operational state, not knowledge:** the build never loads, empties, dumps or snapshots it (`OPERATIONAL` in `build/tables.py`), so a deploy keeps every submission. This doesn't break "files are the truth", because a submission only ever becomes knowledge through a reviewed pull request.
* **Canonicaliser** (`checks/submissions.py`, `canonical_identifier`):
  * Accepts a DOI, PubMed ID, PubMed Central ID or arXiv ID, bare or with a label (`doi:`, `PMID`, `arXiv:`).
  * Also accepts the registries' own URLs for them: doi.org, PubMed, PubMed Central, Europe PMC, arXiv, and bioRxiv and medRxiv content pages.
  * Returns the canonical source ID the data files use. Everything else is refused, including any other URL, link shorteners and text.
* **Vetting** (`vet`): the canonical ID is looked up through the online checks' session (`fetch_source`, ADR 0007) and must exist, must not be retracted (Crossref and PubMed), and must be a kind the allowlist accepts (ADR 0015). The outcome is `accepted`, `malformed`, `unknown`, `retracted` or `not-allowed`. If a registry can't be reached, the outcome is `lookup-failed`, so triage tries again later instead of rejecting.

### Consequences

* Good, because Turnstile and the rate limits can't be bypassed, and a flood can't reach the table without passing them.
* Good, because the canonicaliser and the checks use the same identifiers, registries and allowlist, so a submission accepted by triage cites a source the data checks accept.
* Bad, because the site's server holds the Supabase secret key, which bypasses row-level security on every table. The serving tables are rebuilt from the files on every deploy, so the lasting exposure is the inbox. A dedicated database role for the site is the stricter alternative, if the maintainer prefers.
* Bad, because PubMed Central and arXiv records carry no retraction status, so a retracted paper cited only by those IDs passes vetting. The verifier and review remain the defence.
