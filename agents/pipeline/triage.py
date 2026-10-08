"""Triage (sprint 2.2a, ADR 0028): from each paper's title and abstract, does its own data test a connection?

Abstracts are fetched from Europe PMC at run time and never stored. The verdict, the kinds of evidence, the species
and a one-sentence reason in the model's own words go in corpus/triage.csv. Papers with a verdict from the current
prompt are skipped; papers whose request failed are tried again.
"""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from evals.harness.models import EvidenceClass
from evals.harness.run import read_prompt
from pipeline import europepmc
from pipeline.corpus import CORPUS, Ledger
from pipeline.llm import Request, Result, choose, cost, request_id

PROMPT = Path(__file__).resolve().parents[1] / "roles" / "triage.md"
LEDGER = Ledger(CORPUS / "triage.csv", ("key", "verdict", "basis", "evidence", "species", "reason", "model", "prompt", "date"))
DECIDED = {"in", "out"}
EFFORT, MAX_TOKENS = "low", 8_000


class Verdict(BaseModel):
    """Whether a paper is worth reading for connectivity claims."""

    model_config = ConfigDict(extra="forbid")
    tests_connections: bool = Field(description="The paper's own experiments test a connection by a listed kind of evidence")
    evidence: list[EvidenceClass] = Field(description="The kinds of evidence from the table the paper uses")
    species: list[Literal["mouse", "rat", "human", "other"]] = Field(description="The species studied")
    reason: str = Field(description="One short sentence in your own words, at most 25 words")


def pending(manifest: list[dict], ledger: dict[str, dict], prompt_id: str) -> list[dict]:
    """Papers without a verdict from this prompt: those Europe PMC holds the full text of first, as extraction can
    read them, then the rest, each group in manifest order."""
    todo = [p for p in manifest if not (ledger.get(p["key"], {}).get("verdict") in DECIDED and ledger[p["key"]]["prompt"] == prompt_id)]
    return sorted(todo, key=lambda p: p["full_text"] != "true")


def request_text(paper: dict, abstract: str) -> str:
    return f"Title: {paper['title']}\n\nAbstract: {abstract}" if abstract else f"Title: {paper['title']}\n\nAbstract: (none)"


def row(paper: dict, result: Result, basis: str, model: str, prompt_id: str, today: str) -> dict:
    found = result.parsed
    if found is None:
        return {"key": paper["key"], "verdict": result.stop, "basis": basis, "model": model, "prompt": prompt_id, "date": today}
    return {"key": paper["key"], "verdict": "in" if found.tests_connections else "out", "basis": basis,
            "evidence": ";".join(sorted(set(found.evidence))), "species": ";".join(sorted(set(found.species))),
            "reason": " ".join(found.reason.split())[:300], "model": model, "prompt": prompt_id, "date": today}


def triage(manifest: list[dict], run, limit: int, today: str | None = None, ledger: Ledger | None = None,
           abstract: Callable[[str], str] | None = None, prompt: Path = PROMPT, workers: int = 4) -> dict:
    """Triage up to `limit` pending papers with `run` (a runner from pipeline.llm). Returns a summary."""
    today, ledger, abstract = today or date.today().isoformat(), ledger or LEDGER, abstract or europepmc.abstract
    prompt_id, system = read_prompt(prompt)
    papers = choose(pending(manifest, ledger.read(), prompt_id), run, limit)

    def fetch(paper: dict) -> str | None:
        try:
            return abstract(paper["europe_pmc"])
        except (OSError, ValueError):  # Europe PMC unreachable or answering oddly: try this paper next run
            return None

    with ThreadPoolExecutor(max_workers=workers) as pool:
        abstracts = list(pool.map(fetch, papers))
    fetched = [(p, a) for p, a in zip(papers, abstracts, strict=True) if a is not None]
    requests = [Request(request_id(p["key"]), system, request_text(p, a)) for p, a in fetched]
    results = run.run(requests)
    model = getattr(run, "model", "replay")
    rows = [row(p, results[r.id], "abstract" if a else "title", model, prompt_id, today)
            for (p, a), r in zip(fetched, requests, strict=True)]
    ledger.update(rows)
    usage = {kind: sum(results[r.id].usage.get(kind, 0) for r in requests) for kind in ("input_tokens", "output_tokens",
             "cache_read_input_tokens", "cache_creation_input_tokens")}
    verdicts = [r["verdict"] for r in rows]
    return {"step": "triage", "model": run.name, "prompt": prompt_id, "papers": len(rows),
            "in": verdicts.count("in"), "out": verdicts.count("out"),
            "failed": len(verdicts) - verdicts.count("in") - verdicts.count("out"),
            "unfetched": len(papers) - len(fetched), "without_abstract": sum(1 for _, a in fetched if not a),
            "usage": usage, "cost": cost(model, usage, getattr(run, "batch", False)),
            "remaining": len(pending(manifest, ledger.read(), prompt_id))}
