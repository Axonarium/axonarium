"""Verification (sprint 2.4, ADR 0028): a separate prompt checks each extracted claim against the paper.

For each paper with extracted claims that the current verifier prompt hasn't judged, the verifier reads the same text
the extractor read (pruned and screened) and the paper's claims, numbered and described in words, with each region's
atlas name. It never sees the extractor's reasoning. Each verdict (agree, disagree or unsure) goes in the claim's
`verification`, and the verifier's one-sentence note in `extra` as `verify.note`. Claims stay proposed (ADR 0028).
"""

from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from evals.harness.run import read_prompt
from pipeline import extract
from pipeline.extract import Lexicon
from pipeline.llm import Request, cost

PROMPT = Path(__file__).resolve().parents[1] / "roles" / "verifier.md"
EFFORT, MAX_TOKENS = "medium", 32_000
ORDER = ("id", "subject", "predicate", "object", "species", "evidence_class", "result", "sign", "strength", "measurements",
         "source", "paraphrase", "excerpt", "curation", "verification", "status", "extra")


class ClaimVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim: int = Field(description="The claim's number")
    verdict: Literal["agree", "disagree", "unsure"]
    note: str = Field(description="One short sentence of your own: why, naming the part that is wrong when you disagree")


class Verdicts(BaseModel):
    """A verdict for each numbered claim."""

    model_config = ConfigDict(extra="forbid")
    verdicts: list[ClaimVerdict]


def paper_index(manifest: list[dict]) -> dict[tuple[str, str], dict]:
    """Manifest papers by each identifier they have, as a claim's source cites them."""
    index = {}
    for paper in manifest:
        for kind in ("doi", "pmid", "pmcid"):
            if paper.get(kind):
                index[(kind, paper[kind].lower())] = paper
    return index


def unverified(claims_dir: Path, prompt_id: str, index: dict) -> dict[str, tuple[dict, list[tuple[Path, dict]]]]:
    """Extracted claims this verifier prompt hasn't judged, by paper key: {key: (paper, [(path, record), ...])}."""
    found: dict[str, tuple[dict, list]] = {}
    for path in sorted(claims_dir.glob("*.yaml")):
        record = yaml.safe_load(path.read_text(encoding="utf-8"))
        if record.get("curation", {}).get("role") != "extractor" or record.get("status") == "retracted":
            continue
        if (record.get("verification") or {}).get("prompt") == prompt_id:
            continue
        source = record["source"]
        paper = next((index[(k, str(source[k]).lower())] for k in ("doi", "pmid", "pmcid") if source.get(k)
                      and (k, str(source[k]).lower()) in index), None)
        if paper is not None:
            found.setdefault(paper["key"], (paper, []))[1].append((path, record))
    return found


def _entity(ref: dict, name_in_paper: str | None, lexicon: Lexicon) -> str:
    atlas_name = lexicon.name(ref["id"])
    parts = [f"{ref['id']}" + (f" ({atlas_name})" if atlas_name else "")]
    if name_in_paper:
        parts.append(f'called "{name_in_paper}" in the paper')
    return ", ".join(parts)


def describe(number: int, record: dict, lexicon: Lexicon) -> str:
    extra = record.get("extra") or {}
    return "\n".join([
        f"Claim {number}:",
        f"- subject: {_entity(record['subject'], extra.get('extract.subject_name'), lexicon)}",
        f"- predicate: {record['predicate']}",
        f"- object: {_entity(record['object'], extra.get('extract.object_name'), lexicon)}",
        f"- species: {record['species']}",
        f"- evidence: {record['evidence_class']}",
        f"- result: {record['result']}",
        f"- sign: {record['sign']}",
        f"- locator: {record['source']['locator']}",
        f"- paraphrase: {record['paraphrase']}",
    ])


def record_verdict(path: Path, record: dict, verdict: ClaimVerdict, model: str, prompt_id: str, today: str) -> None:
    record = {**record, "verification": {"by": "agent", "role": "verifier", "model": model, "prompt": prompt_id,
                                         "verdict": verdict.verdict, "date": today},
              "extra": {**(record.get("extra") or {}), "verify.note": " ".join(verdict.note.split())[:500]}}
    ordered = {key: record[key] for key in ORDER if key in record}
    ordered |= {key: value for key, value in record.items() if key not in ordered}
    path.write_text(yaml.safe_dump(ordered, sort_keys=False, allow_unicode=True, width=120), encoding="utf-8")


def verify(manifest: list[dict], run, limit: int, lexicon: Lexicon, classify, today: str | None = None,
           claims_dir: Path | None = None, text: Callable | None = None, prompt: Path = PROMPT) -> dict:
    """Verify the claims of up to `limit` papers with `run` (a runner from pipeline.llm). Returns a summary."""
    today, claims_dir = today or date.today().isoformat(), claims_dir or extract.CLAIMS
    prompt_id, system = read_prompt(prompt)
    model = getattr(run, "model", "replay")
    papers = list(unverified(claims_dir, prompt_id, paper_index(manifest)).values())[:limit]
    requests, sent, skipped = [], {}, []
    for paper, claims in papers:
        try:
            screened = (text or (lambda p: extract.full_text(p, classify)))(paper)
        except (OSError, ValueError, SyntaxError) as error:
            skipped.append(f"{paper['key']}: its text couldn't be read ({type(error).__name__})")
            continue
        if screened.flagged:
            skipped.append(f"{paper['key']}: the hidden-text screen flagged it")
            continue
        listed = "\n\n".join(describe(n, record, lexicon) for n, (_, record) in enumerate(claims, start=1))
        request = Request(f"p{len(requests):05d}", system, f"{screened.text}\n\n## Claims to check\n\n{listed}")
        requests.append(request)
        sent[request.id] = (paper, claims)
    results = run.run(requests)
    counts = {"agree": 0, "disagree": 0, "unsure": 0}
    unjudged = []
    for request in requests:
        paper, claims = sent[request.id]
        result = results[request.id]
        if result.parsed is None:
            unjudged.append(f"{paper['key']}: {result.stop}")
            continue
        by_number = {v.claim: v for v in result.parsed.verdicts}
        for number, (path, record) in enumerate(claims, start=1):
            verdict = by_number.get(number)
            if verdict is None:
                unjudged.append(f"{paper['key']}: claim {record['id']} got no verdict")
                continue
            record_verdict(path, record, verdict, model, prompt_id, today)
            counts[verdict.verdict] += 1
    usage = {kind: sum(results[r.id].usage.get(kind, 0) for r in requests) for kind in ("input_tokens", "output_tokens",
             "cache_read_input_tokens", "cache_creation_input_tokens")}
    return {"step": "verify", "model": run.name, "prompt": prompt_id, "papers": len(papers), "sent": len(requests),
            **counts, "usage": usage, "cost": cost(model, usage, getattr(run, "batch", False)),
            "remaining": len(unverified(claims_dir, prompt_id, paper_index(manifest))),
            "skipped": skipped, "unjudged": unjudged}
