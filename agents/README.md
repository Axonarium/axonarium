# Agents

The prompts that agents work from and the harness that decides which models may fill a role (plan: Agent operating model; [ADR 0020](../docs/decisions/0020-eval-harness.md)). Its own uv project, so model SDKs stay out of the build's environment.

| Path | Holds |
| --- | --- |
| `roles/` | Role prompts, each versioned in its front matter (`id: extract@0.1.0`); a claim records the version that drafted it |
| `evals/` | The eval harness, the gold set (`evals/gold/`, human-owned) and the scored results |

```bash
cd agents
uv run pytest                                      # the harness's tests (pre-commit runs them too)
uv run python -m evals.harness --gold evals/gold/v1 --model anthropic:claude-opus-5-5
```

See [evals/README.md](evals/README.md).
