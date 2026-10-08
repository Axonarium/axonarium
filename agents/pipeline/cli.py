"""Command line: `python -m pipeline <step> [--limit N] [--model provider:model] [--effort level] [--now]`."""

import argparse
import json
import os
import sys

from pipeline import triage
from pipeline.corpus import read_manifest
from pipeline.llm import BatchPending, runner

DEFAULT_MODEL = "anthropic:claude-opus-5-5"


def report(summary: dict) -> str:
    """The run's summary as Markdown, for the terminal and the workflow's step summary."""
    dollars = summary["cost"]
    usage = summary["usage"]
    lines = [f"**{summary['step']}** with {summary['model']} ({summary['prompt']}): {summary['papers']} paper(s)", ""]
    lines += [f"- {key.replace('_', ' ')}: {value}" for key, value in summary.items()
              if key not in {"step", "model", "prompt", "papers", "usage", "cost"}]
    lines += [f"- tokens: {usage['input_tokens']:,} in, {usage['output_tokens']:,} out, "
              f"{usage['cache_read_input_tokens']:,} read from cache, {usage['cache_creation_input_tokens']:,} written to cache",
              f"- cost: {'unknown for this model' if dollars is None else f'${dollars:.2f}'}"]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m pipeline", description="The literature pipeline (ADR 0028).")
    parser.add_argument("step", choices=["triage"], help="which step to run")
    parser.add_argument("--limit", type=int, default=50, help="at most this many papers (default 50)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"anthropic:<model> or replay:<folder> (default {DEFAULT_MODEL})")
    parser.add_argument("--effort", help="the model's effort level (default: the step's own); 'none' to leave it unset")
    parser.add_argument("--now", action="store_true", help="live calls at full price instead of a batch, for small trials")
    args = parser.parse_args(argv)
    effort = None if args.effort == "none" else args.effort or triage.EFFORT
    try:
        run = runner(args.model, triage.Verdict, effort, triage.MAX_TOKENS, batch=not args.now)
        summary = triage.triage(read_manifest(), run, args.limit)
    except BatchPending as pending:
        print(f"batch {pending.batch_id} is still running; nothing was written. Run the step again later: "
              "papers without a verdict are sent again.")
        return 3
    except ValueError as error:
        print(f"{args.step} stopped: {error}")
        return 1
    text = report(summary)
    print(text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(text)
    print(json.dumps(summary), file=sys.stderr)
    return 0
