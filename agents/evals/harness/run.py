"""One eval run: a model and a role prompt against a gold set, scored and reported."""

import argparse
import json
import re
from datetime import date
from pathlib import Path

import yaml

from evals.harness import gold as goldsets
from evals.harness import providers
from evals.harness.score import Tally, score_paper

AGENTS = Path(__file__).resolve().parents[2]
FRONT = re.compile(r"\A---\n(.*?)\n---\n(.*)\Z", re.S)
PROMPT_ID = re.compile(r"^[a-z][a-z0-9_-]*@\d+\.\d+\.\d+$")  # the schema's prompt pattern, such as extract@1.0.0


def read_prompt(path: Path) -> tuple[str, str]:
    """A role prompt's versioned ID (from its front matter) and its text."""
    match = FRONT.match(path.read_text(encoding="utf-8"))
    if not match:
        raise ValueError(f"{path}: a role prompt starts with front matter giving its id, such as id: extract@1.0.0")
    meta = yaml.safe_load(match[1])
    if not isinstance(meta, dict) or not PROMPT_ID.match(str(meta.get("id", ""))):
        raise ValueError(f"{path}: front matter needs an id such as extract@1.0.0")
    return meta["id"], match[2].strip()


def run(gold: goldsets.GoldSet, model: providers.Provider, prompt: Path, effort: str | None, today: str,
        paper_text=goldsets.text) -> dict:
    prompt_id, system = read_prompt(prompt)
    total, papers = Tally(), []
    for paper in gold.papers:
        answer = model.extract(paper.name, system, paper_text(gold, paper))
        predicted = answer.extraction.claims if answer.extraction else []
        tally = score_paper(paper.claims, predicted)
        total.add(tally)
        papers.append({"paper": paper.name, "stop": answer.stop, "detail": answer.detail, "usage": answer.usage,
                       **tally.metrics(), "answer": answer.extraction.model_dump() if answer.extraction else None})
    usage = {k: sum(p["usage"].get(k, 0) for p in papers) for k in ("input_tokens", "output_tokens")}
    return {"date": today, "gold": {"path": str(gold.path), "version": gold.version, "frozen": gold.frozen},
            "model": model.name, "effort": effort, "prompt": prompt_id, **total.metrics(), "usage": usage,
            "failures": {p["paper"]: p["stop"] for p in papers if p["answer"] is None}, "papers": papers}


def _pct(value) -> str:
    return "–" if value is None else f"{value:.1%}"


def markdown(result: dict) -> str:
    counts, fields = result["counts"], result["field_accuracy"]
    lines = [f"# {result['model']} with {result['prompt']} on gold {result['gold']['version']}", "",
             f"Run {result['date']}, effort {result['effort'] or 'default'}.", "",
             "| Precision | Recall | F1 | Method | Result | Sign | Absent recall |", "| --- | --- | --- | --- | --- | --- | --- |",
             f"| {_pct(result['precision'])} | {_pct(result['recall'])} | {_pct(result['f1'])} | "
             f"{_pct(fields['evidence_class'])} | {_pct(fields['result'])} | {_pct(fields['sign'])} | {_pct(result['absent_recall'])} |",
             "", f"{counts['matched']} of {counts['gold']} gold connections found; {counts['predicted']} predicted, "
             f"{counts['direction_errors']} reversed, {counts['species_errors']} in the wrong species. "
             f"Tokens: {result['usage']['input_tokens']} in, {result['usage']['output_tokens']} out.", "",
             "| Paper | Stop | Precision | Recall |", "| --- | --- | --- | --- |"]
    lines += [f"| {p['paper']} | {p['stop']} | {_pct(p['precision'])} | {_pct(p['recall'])} |" for p in result["papers"]]
    return "\n".join(lines) + "\n"


def write(result: dict, out: Path) -> Path:
    """result.json and .md in `out`, named by date, gold version, model and prompt."""
    slug = re.sub(r"[^A-Za-z0-9.@-]+", "-", f"{result['date']}-gold-{result['gold']['version']}-{result['model']}-{result['prompt']}")
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{slug}.json").write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (out / f"{slug}.md").write_text(markdown(result), encoding="utf-8")
    return out / f"{slug}.md"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m evals.harness", description="Score a model and prompt against a gold set.")
    parser.add_argument("--gold", type=Path, required=True, help="the gold set folder, such as evals/gold/v1")
    parser.add_argument("--model", required=True, help="provider:model, such as anthropic:claude-opus-5-5 or openai:<model>")
    parser.add_argument("--prompt", type=Path, default=AGENTS / "roles" / "extractor.md", help="the role prompt")
    parser.add_argument("--effort", default="high", help="the model's effort or reasoning level; 'none' to leave it unset")
    parser.add_argument("--out", type=Path, default=AGENTS / "evals" / "results", help="where to write the report")
    args = parser.parse_args(argv)
    effort = None if args.effort == "none" else args.effort
    try:
        model = providers.provider(args.model, effort)
        result = run(goldsets.load(args.gold), model, args.prompt, effort, date.today().isoformat())
    except ValueError as error:
        print(f"eval stopped: {error}")
        return 1
    report = write(result, args.out)
    print(f"{result['model']} {result['prompt']}: precision {_pct(result['precision'])}, recall {_pct(result['recall'])}; "
          f"report {report}")
    return 0
