"""Extraction (sprint 2.3, ADR 0028): the open full text of triaged papers, as proposed claim files.

For each paper triaged in, with full text in Europe PMC and not yet extracted by the current prompt:

1. its JATS full text is fetched (cached in .cache/papers, never committed) and cut to the parts that hold claims;
2. it passes the hidden-text screen, and a flagged paper is never sent;
3. the extractor drafts claims, with the region lexicon in its instructions;
4. each draft is checked against the lexicon and the schema's rules, and kept drafts become claim files in
   data/claims/amygdala/, status proposed (ADR 0028), citing the paper and naming the model and prompt.

corpus/extracted.csv records what each paper gave.
"""

import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

from evals.harness.models import DraftClaim
from evals.harness.run import read_prompt
from pipeline import europepmc, sections
from pipeline.corpus import CORPUS, ROOT, Ledger
from pipeline.llm import Request, choose, cost, request_id
from pipeline.triage import LEDGER as TRIAGE
from screen import Screened, screen_jats

PROMPT = Path(__file__).resolve().parents[1] / "roles" / "extractor.md"
LEDGER = Ledger(CORPUS / "extracted.csv", ("key", "outcome", "claims", "dropped", "model", "prompt", "date"))
CLAIMS = ROOT / "data" / "claims" / "amygdala"
EFFORT, MAX_TOKENS = "high", 64_000
# Outcomes that mean a paper is done for a prompt version; any other (a refusal, a failed fetch) is tried again.
DONE = {"claims", "none", "screened", "unreadable"}
SPECIES = {"mouse": "NCBITaxon:10090", "rat": "NCBITaxon:10116", "human": "NCBITaxon:9606"}
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


def claim_id(source_key: str, draft: DraftClaim) -> str:
    """A stable ID: the same paper and claim always give the same ID (ADR 0004's shape)."""
    parts = (source_key, draft.subject.id, draft.predicate, draft.object.id, draft.species, draft.evidence_class,
             draft.result, " ".join(draft.locator.split()).lower())
    number = int.from_bytes(hashlib.sha256("\n".join(parts).encode()).digest()[:8], "big")
    return "clm-" + "".join(CROCKFORD[(number >> (5 * i)) & 31] for i in range(10))


def claim(draft: DraftClaim, paper: dict, lexicon: Lexicon, model: str, prompt_id: str, today: str) -> tuple[dict | None, str | None]:
    """A draft as a proposed claim record, or why it was dropped."""
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


def candidates(manifest: list[dict], triaged: dict[str, dict], done: dict[str, dict], prompt_id: str) -> list[dict]:
    """Papers triaged in, whose full text Europe PMC holds, not yet extracted by this prompt; in manifest order."""
    return [p for p in manifest
            if triaged.get(p["key"], {}).get("verdict") == "in" and p["full_text"] == "true" and p["pmcid"]
            and not (done.get(p["key"], {}).get("outcome") in DONE and done[p["key"]]["prompt"] == prompt_id)]


def full_text(paper: dict, classify, fetch: Callable[[str], bytes] | None = None) -> Screened:
    return screen_jats((fetch or europepmc.full_text)(paper["pmcid"]), classify, prune=sections.prune)


def extract(manifest: list[dict], run, limit: int, lexicon: Lexicon, classify, today: str | None = None,
            ledger: Ledger | None = None, triaged: dict | None = None, claims_dir: Path | None = None,
            text: Callable | None = None, prompt: Path = PROMPT) -> dict:
    """Extract up to `limit` candidate papers with `run` (a runner from pipeline.llm). Returns a summary."""
    today, ledger, claims_dir = today or date.today().isoformat(), ledger or LEDGER, claims_dir or CLAIMS
    triaged = triaged if triaged is not None else TRIAGE.read()
    prompt_id, instructions = read_prompt(prompt)
    lexicon.uberon |= set(UBERON.findall(instructions))  # the rat terms in the prompt's own table of names
    system = instructions + "\n\n" + lexicon.text()
    model = getattr(run, "model", "replay")
    papers = choose(candidates(manifest, triaged, ledger.read(), prompt_id), run, limit)
    rows, requests, sent, flagged = [], [], {}, []
    for paper in papers:
        base = {"key": paper["key"], "model": model, "prompt": prompt_id, "date": today}
        try:
            screened = (text or (lambda p: full_text(p, classify)))(paper)
        except (OSError, ValueError, SyntaxError) as error:  # unreachable, or XML that won't parse (ParseError)
            rows.append({**base, "outcome": "unreadable" if isinstance(error, SyntaxError) else "unfetched"})
            continue
        if screened.flagged:  # never sent; its findings go to the maintainer in the run's report
            rows.append({**base, "outcome": "screened"})
            flagged += [f"{paper['key']}: {f.layer}, {f.detail}: {f.excerpt}" for f in screened.findings]
            continue
        request = Request(request_id(paper["key"]), system, screened.text)
        requests.append(request)
        sent[request.id] = (paper, base)
    results = run.run(requests)
    written, dropped_reasons = 0, []
    for request in requests:
        paper, base = sent[request.id]
        result = results[request.id]
        if result.parsed is None:
            rows.append({**base, "outcome": result.stop})
            continue
        kept, dropped = {}, 0
        for draft in result.parsed.claims:
            record, problem = claim(draft, paper, lexicon, model, prompt_id, today)
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
    usage = {kind: sum(results[r.id].usage.get(kind, 0) for r in requests) for kind in ("input_tokens", "output_tokens",
             "cache_read_input_tokens", "cache_creation_input_tokens")}
    outcomes = [r["outcome"] for r in rows]
    return {"step": "extract", "model": run.name, "prompt": prompt_id, "papers": len(rows), "sent": len(requests),
            "claims_written": written, "drafts_dropped": len(dropped_reasons),
            **{f"papers_{outcome}": outcomes.count(outcome) for outcome in sorted(set(outcomes))},
            "usage": usage, "cost": cost(model, usage, getattr(run, "batch", False)),
            "remaining": len(candidates(manifest, triaged, ledger.read(), prompt_id)),
            "dropped": dropped_reasons, "screen_findings": flagged}
