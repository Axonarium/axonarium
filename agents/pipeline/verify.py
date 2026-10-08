"""Verification (sprint 2.4, ADR 0028): a separate prompt checks each extracted claim against the paper.

For each paper with extracted claims no verifier has judged, the verifier reads the same text the extractor read
(pruned and screened) and the paper's claims, numbered and described in words, with each region's atlas name. It never
sees the extractor's reasoning. Each verdict (agree, disagree or unsure) goes in the claim's `verification`, and the
verifier's one-sentence note in `extra` as `verify.note`. Claims stay proposed (ADR 0028). corpus/verified.csv records
each paper's last request. A judged claim is never sent again unless asked for (`--redo`), and a list of claims whose
answers keep failing is set aside after MAX_ATTEMPTS reads (pipeline.corpus).
"""

import hashlib
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from evals.harness.run import read_prompt
from pipeline import extract
from pipeline.corpus import CORPUS, MAX_ATTEMPTS, Ledger, Redo, attempts, recorded
from pipeline.extract import Lexicon
from pipeline.llm import Request, choose, request_id, spend

PROMPT = Path(__file__).resolve().parents[1] / "roles" / "verifier.md"
LEDGER = Ledger(CORPUS / "verified.csv", ("key", "outcome", "claims", "judged", "listed", "attempts", "model", "prompt", "date"))
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


def unverified(claims_dir: Path, prompt_id: str, index: dict, redo: Redo = Redo()) -> dict[str, tuple[dict, list[tuple[Path, dict]]]]:
    """Extracted claims no verifier has judged, or that `redo` asks for again, by paper key:
    {key: (paper, [(path, record), ...])}. A person's verdict is never sent to the model again."""
    found: dict[str, tuple[dict, list]] = {}
    for path in sorted(claims_dir.glob("*.yaml")):
        record = yaml.safe_load(path.read_text(encoding="utf-8"))
        if record.get("curation", {}).get("role") != "extractor" or record.get("status") == "retracted":
            continue
        source = record["source"]
        paper = next((index[(k, str(source[k]).lower())] for k in ("doi", "pmid", "pmcid") if source.get(k)
                      and (k, str(source[k]).lower()) in index), None)
        if paper is None:
            continue
        verification = record.get("verification") or {}
        if verification and (verification.get("by") != "agent" or not redo.wants(paper, verification.get("prompt"), prompt_id)):
            continue
        found.setdefault(paper["key"], (paper, []))[1].append((path, record))
    return found


def request_key(found: tuple[dict, list[tuple[Path, dict]]]) -> str:
    """A paper's request key: its key and the IDs of the claims listed. The verifier answers by claim number, so a
    batch collected later must list exactly the same claims, or it isn't used."""
    paper, claims = found
    return paper["key"] + "|" + ",".join(record["id"] for _, record in claims)


def listed(found: tuple[dict, list[tuple[Path, dict]]]) -> str:
    """A short hash of the paper and the claims listed, kept in the ledger: tries are counted per list of claims."""
    return hashlib.sha256(request_key(found).encode()).hexdigest()[:12]


def last_try(ledger: dict[str, dict], found: tuple[dict, list[tuple[Path, dict]]]) -> dict | None:
    """The ledger's row for this paper, if its last request listed these same claims."""
    row = recorded(ledger, found[0])
    return row if row is not None and row.get("listed") == listed(found) else None


def due(found: tuple[dict, list[tuple[Path, dict]]], ledger: dict[str, dict], prompt_id: str, redo: Redo) -> bool:
    """Whether to send these claims: not tried with this list before, tries left, or asked for again."""
    row = last_try(ledger, found)
    return row is None or redo.wants(found[0], row.get("prompt"), prompt_id) or int(row.get("attempts") or 0) < MAX_ATTEMPTS


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
        *([f"- strength: {record['strength']}"] if record.get("strength") else []),
        *[f"- number: {in_words(m)}" for m in record.get("measurements") or []],
        f"- locator: {record['source']['locator']}",
        f"- paraphrase: {record['paraphrase']}",
    ])


def in_words(m: dict) -> str:
    """A measurement in words, such as "connection probability 0.4 (n = 30)"."""
    unit = "" if m["unit"] == "1" else f" {m['unit']}"
    spread = [f"SD {m['sd']}" if "sd" in m else "", f"SEM {m['sem']}" if "sem" in m else "",
              f"CI {m['ci_low']} to {m['ci_high']}" if "ci_low" in m else "", f"n = {m['n']}" if "n" in m else ""]
    detail = ", ".join(part for part in spread if part)
    return f"{m['quantity'].replace('_', ' ')} {m['value']}{unit}" + (f" ({detail})" if detail else "")


def record_verdict(path: Path, record: dict, verdict: ClaimVerdict, model: str, prompt_id: str, today: str) -> None:
    record = {**record, "verification": {"by": "agent", "role": "verifier", "model": model, "prompt": prompt_id,
                                         "verdict": verdict.verdict, "date": today},
              "extra": {**(record.get("extra") or {}), "verify.note": " ".join(verdict.note.split())[:500]}}
    ordered = {key: record[key] for key in ORDER if key in record}
    ordered |= {key: value for key, value in record.items() if key not in ordered}
    path.write_text(yaml.safe_dump(ordered, sort_keys=False, allow_unicode=True, width=120), encoding="utf-8")


def verify(manifest: list[dict], run, limit: int, lexicon: Lexicon, classify, today: str | None = None,
           claims_dir: Path | None = None, text: Callable | None = None, prompt: Path = PROMPT, ledger: Ledger | None = None,
           redo: Redo = Redo()) -> dict:
    """Verify the claims of up to `limit` papers with `run` (a runner from pipeline.llm). Returns a summary."""
    today, claims_dir, ledger = today or date.today().isoformat(), claims_dir or extract.CLAIMS, ledger or LEDGER
    prompt_id, system = read_prompt(prompt)
    model = getattr(run, "model", "replay")
    before, index = ledger.read(), paper_index(manifest)
    papers = choose([f for f in unverified(claims_dir, prompt_id, index, redo).values() if due(f, before, prompt_id, redo)],
                    run, limit, key=request_key)
    requests, sent, skipped, rows = [], {}, [], []

    def ledger_row(found, outcome: str, stop: str | None, judged: int = 0, answered_by: str | None = None) -> dict:
        return {"key": found[0]["key"], "outcome": outcome, "claims": str(len(found[1])), "judged": str(judged),
                "listed": listed(found), "attempts": attempts(last_try(before, found), stop), "model": answered_by or model,
                "prompt": prompt_id, "date": today}

    for paper, claims in papers:
        try:
            screened = (text or (lambda p: extract.full_text(p, classify)))(paper)
        except (OSError, ValueError, SyntaxError) as error:
            skipped.append(f"{paper['key']}: its text couldn't be read ({type(error).__name__})")
            rows.append(ledger_row((paper, claims), extract.fetch_failure(error), None))
            continue
        if screened.flagged:
            skipped.append(f"{paper['key']}: the hidden-text screen flagged it")
            rows.append(ledger_row((paper, claims), "screened", None))
            continue
        described = "\n\n".join(describe(n, record, lexicon) for n, (_, record) in enumerate(claims, start=1))
        request = Request(request_id(request_key((paper, claims))), system, f"{screened.text}\n\n## Claims to check\n\n{described}")
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
            rows.append(ledger_row((paper, claims), result.stop, result.stop, answered_by=result.model))
            continue
        by_number = {v.claim: v for v in result.parsed.verdicts}
        judged = 0
        for number, (path, record) in enumerate(claims, start=1):
            verdict = by_number.get(number)
            if verdict is None:
                unjudged.append(f"{paper['key']}: claim {record['id']} got no verdict")
                continue
            record_verdict(path, record, verdict, result.model or model, prompt_id, today)
            counts[verdict.verdict] += 1
            judged += 1
        rows.append(ledger_row((paper, claims), "judged", result.stop, judged, result.model))
    ledger.update(rows)
    after = ledger.read()
    left = list(unverified(claims_dir, prompt_id, index).values())
    usage, dollars = spend((results[r.id] for r in requests), model, getattr(run, "batch", False))
    return {"step": "verify", "model": run.name, "prompt": prompt_id, "papers": len(papers), "sent": len(requests),
            **counts, "usage": usage, "cost": dollars,
            "remaining": sum(due(f, after, prompt_id, Redo()) for f in left),
            "skipped": skipped, "unjudged": unjudged,
            "set_aside": [f"{f[0]['key']}: {len(f[1])} claim(s)" for f in left if not due(f, after, prompt_id, Redo())]}
