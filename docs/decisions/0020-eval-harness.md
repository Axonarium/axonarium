---
status: accepted
date: 2026-10-04
decision-makers: Tyler Banks
consulted: Claude (sprint 0.6)
---

# The eval harness: one interface, each model through its provider's official SDK

## Context and Problem Statement

Design principle 4 says any model that passes the gold-set eval can fill a role, and none is hard-wired. The verifier should, where budget allows, come from a different model family than the extractor, so their errors are less correlated. Sprint 0.6 asks for a harness that scores any model and prompt against the gold set. The maintainer asked for it to be built ahead of gold v1 and to support several providers (4 October 2026). How does the harness talk to models, and what does it score?

## Considered Options

* A small provider interface, with each provider called through its own official SDK
* A multi-provider library (such as pydantic-ai or LiteLLM)
* One provider only, with others added later

## Decision Outcome

Chosen option: "a small interface over each provider's official SDK", because the harness asks a model for exactly one thing: a schema-valid list of claims for a paper. Each provider's official SDK does that directly with its own structured-output feature. The official SDKs also follow API changes first, such as new thinking and effort settings and structured-output parameters, where wrappers lag. Each adapter is about 20 lines, so the interface costs little to own.

* **Interface** (`agents/evals/harness/providers.py`): `--model provider:model`.
  * `anthropic:<model>`: the `anthropic` SDK, streamed, with `output_format` set to the extraction schema and effort in `output_config`.
  * `openai:<model>`: the `openai` SDK's `responses.parse` with `text_format`.
  * `replay:<folder>`: saved answers, for tests and re-scoring.

  A new family is one more adapter.
* **No fallbacks:** a refusal, a cut-off answer or output that doesn't fit the schema is recorded as that paper's failure. Server-side fallbacks to another model are never enabled, because an eval must score the model it names.
* **What a model returns** (`models.py`): draft claims with the schema's fields and enumerations, read from `schema/axonarium.yaml`, plus each entity's name as the paper writes it and a paraphrase.
* **Scoring** (`score.py`): connections match on subject, predicate, object and species. Reported scores are precision, recall and F1, field accuracy for method, result and sign, absent recall, direction errors and species errors. These are the plan's metrics, with a separate count for absent results because absence is data.
* **Gold set** (`agents/evals/gold/<version>/`): a manifest, one file per paper (its source, where its text is, its claims), and committed text only for synthetic or openly licensed papers. Open-access text is fetched from Europe PMC when a run needs it, cached, and never committed (ADR 0005). A synthetic placeholder in `evals/fixtures/` exercises the harness until gold v1 exists.
* **Prompts** (`agents/roles/`): Markdown with a versioned `id` in front matter, in the schema's `prompt` pattern (`extract@0.1.0`). A report names the model, prompt version, effort and gold version it scored.
* **Reports** (`agents/evals/results/`): JSON with every paper's raw answer, so a run can be re-scored without calling the model again, and a Markdown summary with token counts.
* **Environment:** `agents/` is its own uv project (`anthropic` 1.11.0, `openai` 3.24.0, `pydantic`, `pyyaml`), like `api/mcp`, with its tests in pre-commit and its lock in Dependabot.

### Consequences

* Good, because the extractor and verifier can come from different families, and adding one is a small, tested change.
* Good, because the harness and its scoring are tested now, with stand-in clients and saved answers, so gold v1 and an API key are all that "two models scored" needs.
* Bad, because the project owns a thin adapter per provider, and each must follow its SDK's structured-output API.
* Neutral: matching on region IDs means the extractor must name regions by ID. The draft prompt (`extract@0.1.0`) gives a table of verified IDs, and sprint 2.3's normaliser may move ID mapping out of the model.
