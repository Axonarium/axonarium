---
status: accepted
date: 2026-10-03
decision-makers: Tyler Banks
---

# HTTP for the online checks: requests-cache, urllib3 Retry and requests-ratelimiter

## Context and Problem Statement

The online checks (ADR 0007) ask Crossref, DataCite, NCBI, OLS, the Allen API and others about every identifier and citation. Sprint 0.3b gave them a hand-written fetcher in `checks/http.py`, with its own on-disk cache, retries, `Retry-After` handling and per-host spacing. The maintainer's standing instruction is to use dedicated packages for infrastructure like this. Which packages replace it?

## Considered Options

* requests with requests-cache, urllib3's `Retry` and requests-ratelimiter
* httpx with hishel (cache) and a transport-level retry
* Keep the hand-written fetcher

## Decision Outcome

Chosen option: "requests, requests-cache, urllib3 `Retry` and requests-ratelimiter", because requests and urllib3 are already the build's HTTP stack (`ingest/`), and the two add-ons come from the same maintainer and are designed to work together.

* **Cache:** requests-cache 1.3.3 with its filesystem backend under `--cache` (`.cache/checks/http`): successful (200) GETs only, kept for seven days, ignoring servers' cache headers and never serving stale answers after an error. `sources --refresh` forces a fresh request and stores it.
* **Retries:** urllib3's `Retry`: four attempts for dropped connections, 429 and 5xx, with exponential backoff, honouring `Retry-After` up to 30 seconds (`retry_after_max`).
* **Spacing:** requests-ratelimiter 0.10.0 (on pyrate-limiter): one request every 0.4 seconds to NCBI, which allows three a second without a key, and every 0.15 seconds to any other host, counted per host. Answers from the cache don't count.
* **What stays ours:** what an answer means: JSON from a 200, nothing for 404 and 410, a failure for anything else, one request per URL per run, and a host given up after it fails every attempt. The checks still fail closed.
* **Tests:** pytest-httpserver 1.1.5 runs a local server, so the retries, `Retry-After` handling and spacing are exercised for real. Only urllib3's sleeps are recorded instead of waited. The recorded registry answers replay through a test-only requests transport.

### Consequences

* Good, because `checks/http.py` holds no cache, retry or rate-limit logic of its own, and the behaviour is the packages' documented behaviour.
* Good, because the same stack can later cache the build's Allen API calls (ADR 0010).
* Bad, because there are three more runtime dependencies (requests-cache, requests-ratelimiter, pyrate-limiter) and one for tests.
