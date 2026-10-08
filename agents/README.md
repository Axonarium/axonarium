# Agents

The prompts that agents work from, the harness that decides which models may fill a role (plan: Agent operating model; [ADR 0020](../docs/decisions/0020-eval-harness.md)), and the screen every paper passes before a model reads it ([ADR 0023](../docs/decisions/0023-hidden-text-screen.md)). Its own uv project, so model SDKs stay out of the build's environment.

| Path | Holds |
| --- | --- |
| `roles/` | Role prompts, each versioned in its front matter (`id: extract@0.1.0`); a claim records the version that drafted it |
| `evals/` | The eval harness, the gold set (`evals/gold/`, human-owned) and the scored results |
| `pipeline/` | The literature pipeline: `python -m pipeline triage` decides which papers to read, on the Batch API; extraction and verification follow ([ADR 0028](../docs/decisions/0028-literature-pipeline.md)) |
| `screen/` | The hidden-text screen: invisible characters and hidden markup stripped, injection-like paragraphs flagged, with planted fixtures (sprint C.5) |

```bash
cd agents
uv run pytest                                      # the harness's and the screen's tests (pre-commit runs them too)
uv run python -m evals.harness --gold evals/gold/v1 --model anthropic:claude-opus-5-5
uv run python -m screen paper.xml                  # what the screen flags in a JATS or text file
uv run python -m pipeline triage --limit 200       # triage the next 200 papers (ANTHROPIC_API_KEY; a batch, half price)
uv run python -m pipeline triage --limit 5 --now   # a small trial with live calls
AXONARIUM_SCREEN_MODEL=1 uv run pytest screen      # with the real classifier (downloads about 740 MB once)
```

A flagged paper is never given to a model. The screen's real classifier is pinned to one revision with its files' hashes; `uv run python -m screen --pin` prints a newer one, and moving to it is a reviewed change.

See [evals/README.md](evals/README.md).
