"""Extraction (sprint 2.3, ADR 0028): the open full text of triaged papers, as proposed claim files.

For each paper triaged in, open access with its full text in Europe PMC, and not yet extracted (pipeline.corpus.due:
once, whatever the prompt version, unless asked for again with --redo):

1. its JATS full text is fetched (cached in .cache/papers, never committed) and cut to the parts that hold claims;
2. it passes the hidden-text screen, and a flagged paper is never sent;
3. the extractor drafts claims, with the region lexicon in its instructions;
4. each draft is checked against the lexicon and the schema's rules, and kept drafts become claim files in
   data/claims/amygdala/, status proposed (ADR 0028), citing the paper and naming the model and prompt.

corpus/extracted.csv records what each paper gave.
"""

import hashlib
import json
import math
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Literal
from urllib.error import HTTPError

import yaml
from pydantic import BaseModel, ConfigDict, Field

from evals.harness.models import DraftClaim, values
from evals.harness.run import read_prompt
from pipeline import europepmc, sections
from pipeline.corpus import CORPUS, ROOT, Ledger, Redo, attempts, due, recorded, set_aside
from pipeline.llm import Request, choose, request_id, spend
from pipeline.triage import LEDGER as TRIAGE
from screen import Screened, screen_jats

PROMPT = Path(__file__).resolve().parents[1] / "roles" / "extractor.md"
LEDGER = Ledger(CORPUS / "extracted.csv", ("key", "outcome", "claims", "dropped", "attempts", "model", "prompt", "date"))
CLAIMS = ROOT / "data" / "claims" / "amygdala"
EFFORT, MAX_TOKENS = "high", 64_000
# Outcomes that mean a paper is done; any other (a refusal, a failed fetch) is tried again while it has tries left.
# `unavailable`: Europe PMC has no full text to give for it.
DONE = {"claims", "none", "screened", "unreadable", "unavailable"}
SPECIES = {"mouse": "NCBITaxon:10090", "rat": "NCBITaxon:10116", "human": "NCBITaxon:9606"}
# The numbers extraction reads, with their unit and range (the data checks' own; checks/file_rules.py). Papers
# normalise projection density each in their own way, so a paper's density isn't comparable with Allen's, which sets
# the brain view's arc widths; it stays in the paraphrase.
QUANTITIES = {
    "connection_probability": ("1", 0.0, 1.0),
    "fraction_of_labelled_neurons": ("1", 0.0, 1.0),
    "synapse_count": ("1", 0.0, math.inf),
    "conduction_delay": ("ms", 0.0, math.inf),
}
EVIDENCE = {  # the schema's predicate rule: each predicate allows only its own kinds of evidence
    "projects_to": {"anterograde_tracer", "retrograde_tracer", "single_neuron_reconstruction"},
    "synapses_onto": {"electron_microscopy", "transsynaptic_tracer"},
    "functionally_connects_to": {"optogenetic_circuit_mapping", "paired_recording", "electrical_stimulation"},
}
CROCKFORD = "0123456789abcdefghjkmnpqrstvwxyz"
CELL_ONTOLOGY = re.compile(r"^CL:\d{7}$")
UBERON = re.compile(r"UBERON:\d{7}")


@dataclass
class Lexicon:
    """What claims may name: each atlas's regions (and the species they belong to), UBERON terms, neuron types."""

    atlases: dict  # atlas id -> {"species": ..., "regions": [...]}, as ingest/lexicon.py writes it
    neuron_types: list[dict]
    uberon: set[str] = field(default_factory=set)  # UBERON terms claims may name, beyond the atlases' mappings

    def __post_init__(self):
        self.region_atlas = {r["id"]: atlas for atlas, entry in self.atlases.items() for r in entry["regions"]}
        self.atlas_species = {atlas: entry["species"] for atlas, entry in self.atlases.items()}
        self.uberon = self.uberon | {r["uberon"] for entry in self.atlases.values() for r in entry["regions"] if r.get("uberon")}
        self.neuron_species = {n["id"]: n["species"] for n in self.neuron_types}
        self.names = {r["id"]: f"{r['acronym']}, {r['name']}" for entry in self.atlases.values() for r in entry["regions"]}
        self.names |= {n["id"]: n["name"] for n in self.neuron_types}

    def name(self, entity_id: str) -> str:
        """A region's atlas acronym and name, or a project neuron type's name; "" for anything else."""
        return self.names.get(entity_id, "")

    @classmethod
    def load(cls, path: Path) -> "Lexicon":
        found = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(found["atlases"], found["neuron_types"])

    def text(self) -> str:
        """The lexicon as the extractor reads it: one line per region or neuron type."""
        lines = ["## Region lexicon", ""]
        for atlas, entry in self.atlases.items():
            species = next((name for name, taxon in SPECIES.items() if taxon == entry["species"]), entry["species"])
            lines += [f"### {atlas} ({species}): ID | acronym | name | UBERON term", ""]
            lines += [f"{r['id']} | {r['acronym']} | {r['name']} | {r.get('uberon') or '-'}" for r in entry["regions"]]
            lines.append("")
        lines += ["## Project neuron types: ID | name | species | region", ""]
        lines += [f"{n['id']} | {n['name']} | {n['species']} | {n['region']}" for n in self.neuron_types]
        return "\n".join(lines) + "\n"

    def entity(self, entity, species: str) -> tuple[dict | None, str | None]:
        """A claim's subject or object as a schema reference, or why it can't be one."""
        if entity.type == "neuron_type":
            if entity.id in self.neuron_species:
                return ({"type": "neuron_type", "id": entity.id}, None) if self.neuron_species[entity.id] == species \
                    else (None, f"{entity.id} is a neuron type of another species")
            return ({"type": "neuron_type", "id": entity.id}, None) if CELL_ONTOLOGY.match(entity.id) \
                else (None, f"{entity.id} is not a project neuron type or a Cell Ontology term")
        atlas = self.region_atlas.get(entity.id)
        if atlas is not None:
            if self.atlas_species[atlas] != species:
                return None, f"{entity.id} is a region of {atlas}, not of {species}"
            return {"type": "region", "id": entity.id, "atlas": atlas}, None
        if entity.id in self.uberon and species != SPECIES["mouse"]:  # mouse claims name Allen regions
            return {"type": "region", "id": entity.id}, None
        return None, f"{entity.id} is not in the region lexicon"


class DraftMeasurement(BaseModel):
    """A number the paper reports for the connection. An unknown part is null; nothing has a default."""

    model_config = ConfigDict(extra="forbid")
    quantity: Literal[tuple(QUANTITIES)]  # type: ignore[valid-type]
    value: float = Field(description="Fractions and probabilities from 0 to 1, never percent; delays in ms")
    sd: float | None
    sem: float | None
    ci_low: float | None
    ci_high: float | None
    n: int | None = Field(description="How many cells, pairs, animals or sections the value comes from")


class Draft(DraftClaim):
    """A draft claim with what the paper says of the connection's strength, and the numbers it reports."""

    strength: Literal[values("OrdinalStrength")] | None = Field(  # type: ignore[valid-type]
        description="Only when the paper itself grades the connection, such as dense or sparse labelling")
    measurements: list[DraftMeasurement] = Field(description="The numbers the paper reports for this connection; empty if none")


class PaperClaims(BaseModel):
    """Every connectivity claim a paper makes, with strength and numbers (the pipeline's extraction; ADR 0028)."""

    model_config = ConfigDict(extra="forbid")
    claims: list[Draft]


def measurements(found: list[DraftMeasurement]) -> tuple[list[dict], list[str]]:
    """The numbers as the schema's measurements, and why any were left out. Each must have its quantity's range."""
    kept, left_out = [], []
    for m in found:
        unit, low, high = QUANTITIES[m.quantity]
        numbers = [x for x in (m.value, m.sd, m.sem, m.ci_low, m.ci_high) if x is not None]
        problem = (
            "isn't a finite number" if not all(math.isfinite(x) for x in numbers)
            else f"{m.value} is outside [{low}, {high}]" + (", perhaps a percent" if unit == "1" and high == 1 and m.value <= 100 else "")
            if not low <= m.value <= high
            else "has a negative spread" if any(x is not None and x < 0 for x in (m.sd, m.sem))
            else "needs both ends of its interval" if (m.ci_low is None) != (m.ci_high is None)
            else "has an interval whose low end is above its high end" if m.ci_low is not None and m.ci_low > m.ci_high
            else "has a sample size below 1" if m.n is not None and m.n < 1
            else None
        )
        if problem:
            left_out.append(f"{m.quantity} {problem}")
            continue
        kept.append({"quantity": m.quantity, "value": m.value, "unit": unit,
                     **{k: v for k, v in (("sd", m.sd), ("sem", m.sem), ("ci_low", m.ci_low), ("ci_high", m.ci_high), ("n", m.n))
                        if v is not None}})
    return kept, left_out


def claim_id(source_key: str, draft: DraftClaim) -> str:
    """A stable ID: the same paper and claim always give the same ID (ADR 0004's shape)."""
    parts = (source_key, draft.subject.id, draft.predicate, draft.object.id, draft.species, draft.evidence_class,
             draft.result, " ".join(draft.locator.split()).lower())
    number = int.from_bytes(hashlib.sha256("\n".join(parts).encode()).digest()[:8], "big")
    return "clm-" + "".join(CROCKFORD[(number >> (5 * i)) & 31] for i in range(10))


def claim(draft: DraftClaim, paper: dict, lexicon: Lexicon, model: str, prompt_id: str, today: str,
          notes: list[str] | None = None) -> tuple[dict | None, str | None]:
    """A draft as a proposed claim record, or why it was dropped. Numbers left out of a kept claim are added to
    `notes`. An absent result keeps no strength or numbers, as the schema's rules require."""
    if draft.species not in SPECIES.values():
        return None, f"species {draft.species} is outside the project's species"
    if draft.evidence_class not in EVIDENCE[draft.predicate]:
        return None, f"{draft.evidence_class} can't show {draft.predicate}"
    if draft.subject.id == draft.object.id:
        return None, f"{draft.subject.id} connects to itself"
    subject, problem = lexicon.entity(draft.subject, draft.species)
    if subject is None:
        return None, problem
    target, problem = lexicon.entity(draft.object, draft.species)
    if target is None:
        return None, problem
    source = {k: paper[k] for k in ("doi", "pmid", "pmcid") if paper.get(k)}
    record = {
        "id": claim_id(paper["key"], draft),
        "subject": subject,
        "predicate": draft.predicate,
        "object": target,
        "species": draft.species,
        "evidence_class": draft.evidence_class,
        "result": draft.result,
        "sign": "unknown" if draft.result == "absent" else draft.sign,
    }
    if draft.result != "absent" and getattr(draft, "strength", None):
        record["strength"] = draft.strength
    if draft.result != "absent" and getattr(draft, "measurements", None):
        kept, left_out = measurements(draft.measurements)
        if kept:
            record["measurements"] = kept
        if notes is not None:
            notes += [f"{paper['key']}: {draft.subject.id} → {draft.object.id}: {problem}" for problem in left_out]
    record |= {
        "source": {**source, "locator": " ".join(draft.locator.split())},
        "paraphrase": " ".join(draft.paraphrase.split()),
        "curation": {"by": "agent", "role": "extractor", "model": model, "prompt": prompt_id, "date": today},
        "status": "proposed",
        "extra": {"extract.subject_name": draft.subject.name_in_paper, "extract.object_name": draft.object.name_in_paper},
    }
    return record, None


def write(record: dict, folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{record['id']}.yaml"
    path.write_text(yaml.safe_dump(record, sort_keys=False, allow_unicode=True, width=120), encoding="utf-8")
    return path


def candidates(manifest: list[dict], triaged: dict[str, dict], done: dict[str, dict], prompt_id: str,
               redo: Redo = Redo()) -> list[dict]:
    """Papers triaged in, open access with their full text in Europe PMC, due for extraction (pipeline.corpus.due); in
    manifest order. Europe PMC serves full text only for its open-access subset: it holds other papers' text, such as
    author manuscripts, but won't give it out."""
    return [p for p in manifest
            if (recorded(triaged, p) or {}).get("verdict") == "in" and p["full_text"] == "true" and p["open_access"] == "true"
            and p["pmcid"] and due(p, recorded(done, p), "outcome", DONE, prompt_id, redo)]


def fetch_failure(error: Exception) -> str:
    """A ledger outcome for a full text that couldn't be read: `unreadable` XML, `unavailable` text (Europe PMC answers
    that it has none), or `unfetched` (Europe PMC unreachable; tried again next run)."""
    if isinstance(error, SyntaxError):
        return "unreadable"
    return "unavailable" if isinstance(error, HTTPError) and error.code == 404 else "unfetched"


def why(error: Exception) -> str:
    """A failed fetch's cause for the run's report, such as `HTTPError 429` or `URLError: timed out`."""
    if isinstance(error, HTTPError):
        return f"HTTPError {error.code}"
    return f"{type(error).__name__}: {str(error)[:120]}" if str(error) else type(error).__name__


def full_text(paper: dict, classify, fetch: Callable[[str], bytes] | None = None) -> Screened:
    return screen_jats((fetch or europepmc.full_text)(paper["pmcid"]), classify, prune=sections.prune)


def extract(manifest: list[dict], run, limit: int, lexicon: Lexicon, classify, today: str | None = None,
            ledger: Ledger | None = None, triaged: dict | None = None, claims_dir: Path | None = None,
            text: Callable | None = None, prompt: Path = PROMPT, redo: Redo = Redo()) -> dict:
    """Extract up to `limit` candidate papers with `run` (a runner from pipeline.llm). Returns a summary."""
    today, ledger, claims_dir = today or date.today().isoformat(), ledger or LEDGER, claims_dir or CLAIMS
    triaged = triaged if triaged is not None else TRIAGE.read()
    prompt_id, instructions = read_prompt(prompt)
    lexicon.uberon |= set(UBERON.findall(instructions))  # the rat terms in the prompt's own table of names
    system = instructions + "\n\n" + lexicon.text()
    model = getattr(run, "model", "replay")
    before = ledger.read()
    papers = choose(candidates(manifest, triaged, before, prompt_id, redo), run, limit)
    rows, requests, sent, flagged, failed = [], [], {}, [], []
    for paper in papers:
        base = {"key": paper["key"], "attempts": attempts(recorded(before, paper), None), "model": model, "prompt": prompt_id,
                "date": today}
        try:
            screened = (text or (lambda p: full_text(p, classify)))(paper)
        except (OSError, ValueError, SyntaxError) as error:  # unreachable, or XML that won't parse (ParseError)
            rows.append({**base, "outcome": fetch_failure(error)})
            failed.append(f"{paper['key']}: {why(error)}")
            continue
        if screened.flagged:  # never sent; its findings go to the maintainer in the run's report
            rows.append({**base, "outcome": "screened"})
            flagged += [f"{paper['key']}: {f.layer}, {f.detail}: {f.excerpt}" for f in screened.findings]
            continue
        request = Request(request_id(paper["key"]), system, screened.text)
        requests.append(request)
        sent[request.id] = (paper, base)
    results = run.run(requests)
    written, dropped_reasons, numbers_left_out = 0, [], []
    for request in requests:
        paper, base = sent[request.id]
        result = results[request.id]
        answered_by = result.model or model
        base = {**base, "attempts": attempts(recorded(before, paper), result.stop), "model": answered_by}
        if result.parsed is None:
            rows.append({**base, "outcome": result.stop})
            continue
        kept, dropped = {}, 0
        for draft in result.parsed.claims:
            record, problem = claim(draft, paper, lexicon, answered_by, prompt_id, today, numbers_left_out)
            if record is None:
                dropped += 1
                dropped_reasons.append(f"{paper['key']}: {problem}")
            else:
                kept[record["id"]] = record  # the same claim drafted twice is one file
        for record in kept.values():
            write(record, claims_dir)
        written += len(kept)
        rows.append({**base, "outcome": "claims" if kept else "none", "claims": str(len(kept)), "dropped": str(dropped)})
    ledger.update(rows)
    usage, dollars = spend((results[r.id] for r in requests), model, getattr(run, "batch", False))
    outcomes = [r["outcome"] for r in rows]
    return {"step": "extract", "model": run.name, "prompt": prompt_id, "papers": len(rows), "sent": len(requests),
            "claims_written": written, "drafts_dropped": len(dropped_reasons),
            **{f"papers_{outcome}": outcomes.count(outcome) for outcome in sorted(set(outcomes))},
            "usage": usage, "cost": dollars,
            "remaining": len(candidates(manifest, triaged, ledger.read(), prompt_id)),
            "set_aside": set_aside([p for p in manifest if (recorded(triaged, p) or {}).get("verdict") == "in"], ledger.read(),
                                   "outcome", DONE),
            "dropped": dropped_reasons, "numbers_left_out": numbers_left_out, "screen_findings": flagged,
            "not_read": failed}
