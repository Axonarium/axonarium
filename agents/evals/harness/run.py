"""One eval run: a model and a role prompt against a gold set, scored and reported."""

import argparse
import hashlib
import json
import re
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path

import screen
from evals.harness import gold as goldsets
from evals.harness import providers
from evals.harness.score import Tally, score_paper
from pipeline import extract
from screen.injection import ProtectAI

AGENTS = Path(__file__).resolve().parents[2]
LEXICON = AGENTS.parent / ".cache" / "lexicon.json"  # where `python -m ingest.lexicon` writes it for the pipeline
PRUNED = "JATS cut to the title, abstract, methods, results and captions (pipeline.sections)"


def lexicon_file(path: Path) -> dict:
    """What a report says of the lexicon: its file, the day it was written and a hash of its content."""
    written = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).date().isoformat()
    return {"path": str(path), "date": written, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def run(gold: goldsets.GoldSet, model: providers.Provider, prompt: Path, lexicon: extract.Lexicon, effort: str | None,
        today: str, paper_text, about_lexicon: dict | None = None) -> dict:
    """`paper_text(gold, paper)` gives a paper's screened text. The model gets the instructions the pipeline gives
    its extractor: the role prompt and the region lexicon. A flagged paper is never sent to the model: it is
    reported, and its gold claims count as missed."""
    prompt_id, system = extract.system_prompt(prompt, lexicon)
    total, papers = Tally(), []
    for paper in gold.papers:
        screened = paper_text(gold, paper)
        if screened.flagged:
            tally = score_paper(paper.claims, [])
            total.add(tally)
            papers.append({"paper": paper.name, "stop": "screened", "detail": None, "usage": {}, **tally.metrics(),
                           "answer": None, "screen": [asdict(f) for f in screened.findings]})
            continue
        answer = model.extract(paper.name, system, screened.text)
        predicted = answer.extraction.claims if answer.extraction else []
        tally = score_paper(paper.claims, predicted)
        total.add(tally)
        papers.append({"paper": paper.name, "stop": answer.stop, "detail": answer.detail, "usage": answer.usage,
                       **tally.metrics(), "answer": answer.extraction.model_dump() if answer.extraction else None})
    usage = {k: sum(p["usage"].get(k, 0) for p in papers) for k in ("input_tokens", "output_tokens")}
    return {"date": today, "gold": {"path": str(gold.path), "version": gold.version, "frozen": gold.frozen},
            "model": model.name, "effort": effort, "prompt": prompt_id, "lexicon": about_lexicon, "text": PRUNED,
            **total.metrics(), "usage": usage,
            "failures": {p["paper"]: p["stop"] for p in papers if p["answer"] is None},
            "screened": [p["paper"] for p in papers if p["stop"] == "screened"], "papers": papers}


def _pct(value) -> str:
    return "–" if value is None else f"{value:.1%}"


def _lexicon(about: dict | None) -> str:
    return f"Lexicon of {about['date']} (sha256 {about['sha256'][:12]})." if about else "Lexicon unrecorded."


def markdown(result: dict) -> str:
    counts, fields = result["counts"], result["field_accuracy"]
    lines = [f"# {result['model']} with {result['prompt']} on gold {result['gold']['version']}", "",
             f"Run {result['date']}, effort {result['effort'] or 'default'}. {_lexicon(result['lexicon'])} "
             f"{result['text']}.", "",
             "| Precision | Recall | F1 | Method | Result | Sign | Absent recall |", "| --- | --- | --- | --- | --- | --- | --- |",
             f"| {_pct(result['precision'])} | {_pct(result['recall'])} | {_pct(result['f1'])} | "
             f"{_pct(fields['evidence_class'])} | {_pct(fields['result'])} | {_pct(fields['sign'])} | {_pct(result['absent_recall'])} |",
             "", f"{counts['matched']} of {counts['gold']} gold connections found; {counts['predicted']} predicted, "
             f"{counts['direction_errors']} reversed, {counts['species_errors']} in the wrong species. "
             f"Tokens: {result['usage']['input_tokens']} in, {result['usage']['output_tokens']} out.", "",
             "| Paper | Stop | Precision | Recall |", "| --- | --- | --- | --- |"]
    lines += [f"| {p['paper']} | {p['stop']} | {_pct(p['precision'])} | {_pct(p['recall'])} |" for p in result["papers"]]
    for paper in (p for p in result["papers"] if p["stop"] == "screened"):
        lines += ["", f"**{paper['paper']}** was flagged by the hidden-text screen and not read by the model:", ""]
        lines += [f"- {f['layer']}, {f['detail']}: {f['excerpt']}" for f in paper["screen"]]
    return "\n".join(lines) + "\n"


def write(result: dict, out: Path) -> Path:
    """result.json and .md in `out`, named by date, gold version, model and prompt."""
    slug = re.sub(r"[^A-Za-z0-9.@-]+", "-", f"{result['date']}-gold-{result['gold']['version']}-{result['model']}-{result['prompt']}")
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{slug}.json").write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (out / f"{slug}.md").write_text(markdown(result), encoding="utf-8")
    return out / f"{slug}.md"


def main(argv: list[str] | None = None, classify=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m evals.harness", description="Score a model and prompt against a gold set.")
    parser.add_argument("--gold", type=Path, required=True, help="the gold set folder, such as evals/gold/v1")
    parser.add_argument("--model", required=True, help="provider:model, such as anthropic:claude-opus-5-5 or openai:<model>")
    parser.add_argument("--prompt", type=Path, default=AGENTS / "roles" / "extractor.md", help="the role prompt")
    parser.add_argument("--lexicon", type=Path, default=LEXICON,
                        help="the region lexicon from `python -m ingest.lexicon`, as the pipeline reads it (default .cache/lexicon.json)")
    parser.add_argument("--effort", default="high", help="the model's effort or reasoning level; 'none' to leave it unset")
    parser.add_argument("--out", type=Path, default=AGENTS / "evals" / "results", help="where to write the report")
    args = parser.parse_args(argv)
    effort = None if args.effort == "none" else args.effort
    try:
        model = providers.provider(args.model, effort)
        gold = goldsets.load(args.gold)
        if not args.lexicon.is_file():
            raise ValueError(f"no lexicon at {args.lexicon}; write one from the repository root with "
                             "`uv run python -m ingest.lexicon --out .cache/lexicon.json`")
        lexicon = extract.Lexicon.load(args.lexicon)
        classify = classify or ProtectAI()
        problems = screen.preflight(classify)
        if problems:
            raise ValueError("the hidden-text screen fails its fixtures: " + "; ".join(problems))
        result = run(gold, model, args.prompt, lexicon, effort, date.today().isoformat(),
                     lambda g, paper: goldsets.text(g, paper, classify), lexicon_file(args.lexicon))
    except ValueError as error:
        print(f"eval stopped: {error}")
        return 1
    report = write(result, args.out)
    print(f"{result['model']} {result['prompt']}: precision {_pct(result['precision'])}, recall {_pct(result['recall'])}; "
          f"report {report}")
    return 0
