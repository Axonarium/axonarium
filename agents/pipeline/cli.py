"""Command line: `python -m pipeline <step> [--limit N] [--model provider:model] [--effort level] [--now]`."""

import argparse
import json
import os
import sys

from evals.harness.models import Extraction
from pipeline import extract, triage, verify
from pipeline.corpus import ROOT, read_manifest
from pipeline.llm import BatchPending, runner

DEFAULT_MODEL = "anthropic:claude-opus-5-5"
LEXICON = ROOT / ".cache" / "lexicon.json"
SHOWN = 30  # list entries (dropped drafts, screen findings) shown in a report


def report(summary: dict) -> str:
    """The run's summary as Markdown, for the terminal and the workflow's step summary."""
    dollars, usage = summary["cost"], summary["usage"]
    lines = [f"**{summary['step']}** with {summary['model']} ({summary['prompt']}): {summary['papers']} paper(s)", ""]
    lists = {key: value for key, value in summary.items() if isinstance(value, list)}
    lines += [f"- {key.replace('_', ' ')}: {value}" for key, value in summary.items()
              if key not in {"step", "model", "prompt", "papers", "usage", "cost"} and key not in lists]
    lines += [f"- tokens: {usage['input_tokens']:,} in, {usage['output_tokens']:,} out, "
              f"{usage['cache_read_input_tokens']:,} read from cache, {usage['cache_creation_input_tokens']:,} written to cache",
              f"- cost: {'unknown for this model' if dollars is None else f'${dollars:.2f}'}"]
    for key, entries in lists.items():
        if entries:
            lines += ["", f"{key.replace('_', ' ').capitalize()} ({len(entries)}):", ""]
            lines += [f"- {entry}" for entry in entries[:SHOWN]]
            lines += [f"- … and {len(entries) - SHOWN} more"] if len(entries) > SHOWN else []
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None, classify=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m pipeline", description="The literature pipeline (ADR 0028).")
    parser.add_argument("step", choices=["triage", "extract", "verify"], help="which step to run")
    parser.add_argument("--limit", type=int, default=50, help="at most this many papers (default 50)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"anthropic:<model> or replay:<folder> (default {DEFAULT_MODEL})")
    parser.add_argument("--effort", help="the model's effort level (default: the step's own); 'none' to leave it unset")
    parser.add_argument("--now", action="store_true", help="live calls at full price instead of a batch, for small trials")
    parser.add_argument("--lexicon", default=LEXICON, help="extract and verify: the region lexicon from `python -m ingest.lexicon`")
    args = parser.parse_args(argv)
    step = {"triage": triage, "extract": extract, "verify": verify}[args.step]
    effort = None if args.effort == "none" else args.effort or step.EFFORT
    schema = {"triage": triage.Verdict, "extract": Extraction, "verify": verify.Verdicts}[args.step]
    try:
        run = runner(args.model, schema, effort, step.MAX_TOKENS, batch=not args.now)
        if args.step == "triage":
            summary = triage.triage(read_manifest(), run, args.limit)
        else:
            from screen import preflight
            from screen.injection import ProtectAI

            classify = classify or ProtectAI()
            problems = preflight(classify)
            if problems:
                raise ValueError("the hidden-text screen fails its fixtures: " + "; ".join(problems))
            work = extract.extract if args.step == "extract" else verify.verify
            summary = work(read_manifest(), run, args.limit, extract.Lexicon.load(args.lexicon), classify)
    except BatchPending as pending:
        print(f"batch {pending.batch_id} is still running; nothing was written. Run the step again later: "
              "papers without a result are sent again.")
        return 3
    except (ValueError, FileNotFoundError) as error:
        print(f"{args.step} stopped: {error}")
        return 1
    text = report(summary)
    print(text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(text)
    print(json.dumps(summary), file=sys.stderr)
    return 0
