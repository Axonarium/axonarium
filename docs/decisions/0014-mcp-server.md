---
status: accepted
date: 2026-10-04
decision-makers: Tyler Banks
---

# MCP server: the official Python SDK over the read API

## Context and Problem Statement

Sprint 3.4 asks for an MCP server so that an LLM agent can answer a pathway question with citations. What does it build on, and how do people run it?

## Considered Options

* The official MCP Python SDK (`mcp`), reading the public read API (ADR 0013) with httpx, as a small package in `api/mcp`
* A TypeScript server with the official TypeScript SDK, inside the site
* Tools that query Supabase directly

## Decision Outcome

Chosen option: "the official Python SDK over the read API", because the SDK is the reference implementation, the read API is already the stable contract (and states each claim's reuse terms), and a separate package runs anywhere with one `uvx` command.

* **Package:** `axonarium-mcp` in `api/mcp`, with its own `pyproject.toml` and `uv.lock`; dependencies `mcp` 2.3.0 (`MCPServer`) and httpx 0.28.1. Run with `uvx --from "git+https://github.com/axonarium/axonarium#subdirectory=api/mcp" axonarium-mcp` over stdio.
* **Tools:** `search_regions`, `region_connections`, `find_connections` and `connection_evidence`, all marked read-only. Evidence comes back ready to cite: the finding, projection density, accepted or proposed, the source URL and locator, and the reuse terms. Unknown IDs and bad parameters are tool errors with the API's message.
* **Instructions:** the server tells the agent to cite claims with their sources, to explain proposed claims, and to state the Allen terms.
* **Tests:** the tools are called through the MCP protocol in-process (`mcp.Client`) against canned API answers (httpx `MockTransport`); a pre-commit hook runs them in CI, and Dependabot updates the package's lock.

### Consequences

* Good, because any MCP client can use Axonarium with one command, and answers carry their citations and terms.
* Good, because the server holds no data or secrets: it only reads the public API.
* Bad, because the server depends on the API's availability, and is not yet on PyPI (the `axonarium` names there are still to be claimed).
