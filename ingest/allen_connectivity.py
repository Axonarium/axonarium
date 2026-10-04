"""Region-level connectivity claims from the Allen Mouse Brain Connectivity Atlas, made at build time (ADR 0010).

Allen terms allow non-commercial use but not commercial redistribution, so these claims are never committed and
never dumped (ADR 0005); the live site shows them with the citation. Each claim is one experiment's projection
into one target, from wild-type mice: every target of injections in the amygdala (its outputs), and the amygdala
targets of injections anywhere else (its inputs).
"""

import hashlib
from collections.abc import Callable
from urllib.parse import quote

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

API = "https://api.brain-map.org/api/v2/data/query.json?criteria={criteria}&num_rows={num_rows}&start_row={start_row}"
PROJECTION_PRODUCT = 5  # Mouse Connectivity: Projection
SUMMARY_STRUCTURES = 167587189  # "Brain – Summary Structures", the 316 targets Allen's own analyses use
ROOT = 997  # Its injection volume is the whole injection's.
PAGE = 2000
BATCH = 50  # experiments per injection-volume query
DENSITY_MIN = 0.01
SHARE_MIN = 0.5  # Below this share of the injection in the primary structure, claims are proposed, not accepted.
SOURCE = {"doi": "10.1038/nature13186"}  # Oh et al. 2014, "A mesoscale connectome of the mouse brain"
# Ingesters are agents without a language model: `model` says so, and `prompt` is the adapter's versioned procedure.
# Bump the version whenever the adapter's output changes; it and the date keep reruns identical (ADR 0010).
MODEL = "deterministic-adapter"
PROCEDURE = "allen-connectivity@1.2.0"
ADAPTER_DATE = "2026-10-03"
CROCKFORD = "0123456789abcdefghjkmnpqrstvwxyz"
USER_AGENT = {"User-Agent": "axonarium-build (https://github.com/axonarium/axonarium)"}


def _session() -> requests.Session:
    session = requests.Session()
    retry = Retry(total=4, backoff_factor=1, status_forcelist=(429, 500, 502, 503, 504), allowed_methods=("GET",))
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update(USER_AGENT)
    return session


def _get(criteria: str, num_rows: int = PAGE, session: requests.Session | None = None, start_row: int = 0) -> list[dict]:
    """The rows an Allen API RMA query returns; an unsuccessful query is an error."""
    url = API.format(criteria=quote(criteria, safe="[]$:,'()="), num_rows=num_rows, start_row=start_row)
    response = (session or _session()).get(url, timeout=120)
    response.raise_for_status()
    body = response.json()
    if not body.get("success"):
        raise RuntimeError(f"Allen API query failed: {str(body.get('msg'))[:200]}")
    return body["msg"]


def claim_id(experiment: int, target: int) -> str:
    """A stable claim ID: the same experiment and target always give the same ID (ADR 0004's shape)."""
    number = int.from_bytes(hashlib.sha256(f"allen-connectivity:{experiment}:{target}".encode()).digest()[:8], "big")
    return "clm-" + "".join(CROCKFORD[(number >> (5 * i)) & 31] for i in range(10))


def paged(get: Callable, criteria: str, page: int = PAGE) -> list[dict]:
    """Every row of a query, a page at a time, in ID order so pages don't shift."""
    criteria += ",rma::options[order$eq'id']"
    rows: list[dict] = []
    while True:
        found = get(criteria, page, start_row=len(rows))
        rows.extend(found)
        if len(found) < page:
            return rows


def experiments(get: Callable) -> list[dict]:
    """Wild-type projection experiments that passed QC and have one injection, with its primary structure."""
    criteria = (f"model::SectionDataSet,rma::criteria,[failed$eqfalse],products[id$eq{PROJECTION_PRODUCT}],"
                "rma::include,specimen(donor(transgenic_lines)),specimen(stereotaxic_injections(primary_injection_structure))")
    found = []
    for row in paged(get, criteria):
        specimen = row["specimen"]
        if specimen["donor"].get("transgenic_lines"):
            continue  # Cre lines label cell types: neuron-type claims, a later sprint.
        if len(specimen["stereotaxic_injections"]) != 1:
            continue  # Labelling couldn't be attributed to one injection site.
        found.append({"id": row["id"], "injection": specimen["stereotaxic_injections"][0]["primary_injection_structure"]["id"]})
    return sorted(found, key=lambda e: e["id"])


def summary_structures(get: Callable) -> set[int]:
    return {row["id"] for row in get(f"model::Structure,rma::criteria,structure_sets[id$eq{SUMMARY_STRUCTURES}]", 2000)}


def injections(get: Callable, found: list[dict], summary: set[int]) -> dict[int, tuple[float, set[int]]]:
    """Per experiment: the primary structure's share of the injected volume, and every summary structure that
    received tracer."""
    wanted = summary | {e["injection"] for e in found} | {ROOT}
    volumes: dict[int, dict[int, float]] = {e["id"]: {} for e in found}
    ids = sorted(volumes)
    for start in range(0, len(ids), BATCH):
        batch = ",".join(map(str, ids[start:start + BATCH]))
        for r in paged(get, f"model::ProjectionStructureUnionize,rma::criteria,[section_data_set_id$in{batch}],"
                            "[is_injection$eqtrue],[hemisphere_id$eq3]"):
            if r["structure_id"] in wanted and r["projection_volume"] > 0:
                volumes[r["section_data_set_id"]][r["structure_id"]] = r["projection_volume"]
    shares = {}
    for e in found:
        v = volumes[e["id"]]
        shares[e["id"]] = (v.get(e["injection"], 0) / v[ROOT] if v.get(ROOT) else 0.0, {s for s in v if s in summary})
    return shares


def projections(get: Callable, experiment: int) -> list[dict]:
    """Projection density per structure, both hemispheres, outside the injection site."""
    return paged(get, f"model::ProjectionStructureUnionize,rma::criteria,[section_data_set_id$eq{experiment}],"
                      "[is_injection$eqfalse],[hemisphere_id$eq3]")


def projections_into(get: Callable, targets: list[int]) -> dict[int, list[dict]]:
    """Per experiment, its projections into these structures at or above DENSITY_MIN, both hemispheres."""
    rows = paged(get, f"model::ProjectionStructureUnionize,rma::criteria,[structure_id$in{','.join(map(str, targets))}],"
                      f"[is_injection$eqfalse],[hemisphere_id$eq3],[projection_density$ge{DENSITY_MIN}]")
    found: dict[int, list[dict]] = {}
    for row in rows:
        found.setdefault(row["section_data_set_id"], []).append(row)
    return found


def build_claims(atlas: str, found: list[dict], summary: set[int], projected: dict[int, list[dict]],
                 acronyms: dict[int, str]) -> list[dict]:
    """One claim per experiment and summary-structure target (in the pinned atlas) with density at or above DENSITY_MIN."""
    claims = []
    for experiment in found:
        injection = experiment["injection"]
        for row in projected[experiment["id"]]:
            target, density = row["structure_id"], row["projection_density"]
            # Skip the injection site and any target that received tracer (spill-over labels it locally), targets
            # outside the summary set or the pinned atlas, and weak densities.
            if target == injection or target in experiment["injected"] or target not in summary or target not in acronyms \
                    or density < DENSITY_MIN:
                continue
            value = round(density, 6)
            claims.append({
                "id": claim_id(experiment["id"], target),
                "subject": {"type": "region", "id": f"MBA:{injection}", "atlas": atlas},
                "predicate": "projects_to",
                "object": {"type": "region", "id": f"MBA:{target}", "atlas": atlas},
                "species": "NCBITaxon:10090",
                "evidence_class": "anterograde_tracer",
                "result": "present",
                "sign": "unknown",
                "measurements": [{"quantity": "projection_density", "value": value, "unit": "1"}],
                "source": {**SOURCE, "locator": f"Allen Mouse Brain Connectivity Atlas, experiment {experiment['id']}"},
                "paraphrase": (f"In Allen Mouse Brain Connectivity Atlas experiment {experiment['id']}, an anterograde "
                               f"tracer injected into {acronyms.get(injection, injection)} of a wild-type mouse "
                               f"({experiment['share']:.0%} of the injection in {acronyms.get(injection, injection)}) "
                               f"labelled axons in {acronyms.get(target, target)} (projection density {value:.3f})."),
                "curation": {"by": "agent", "role": "ingester", "model": MODEL, "prompt": PROCEDURE, "date": ADAPTER_DATE},
                "status": "accepted" if experiment["share"] >= SHARE_MIN else "proposed",
                "extra": {"allen.experiment": experiment["id"], "allen.injection_share": round(experiment["share"], 2)},
            })
    return sorted(claims, key=lambda claim: claim["id"])


def load_claims(atlas: str, structure_ids: list[int], acronyms: dict[int, str], get: Callable | None = None) -> list[dict]:
    """The claims for these structures (the amygdala and its subdivisions): every target of wild-type injections
    into them, and every one of them that injections elsewhere reach."""
    if not structure_ids:
        return []
    if get is None:
        session = _session()
        get = lambda criteria, num_rows=PAGE, start_row=0: _get(criteria, num_rows, session, start_row)  # noqa: E731
    amygdala = set(structure_ids)
    found = [e for e in experiments(get) if e["injection"] in acronyms]  # injection sites the pinned atlas has
    summary = summary_structures(get)
    outputs = [e for e in found if e["injection"] in amygdala]
    into = projections_into(get, sorted(amygdala & summary))
    inputs = [e for e in found if e["injection"] not in amygdala and e["id"] in into]
    projected = {e["id"]: projections(get, e["id"]) for e in outputs} | {e["id"]: into[e["id"]] for e in inputs}
    chosen = sorted(outputs + inputs, key=lambda e: e["id"])
    shares = injections(get, chosen, summary)
    for experiment in chosen:
        experiment["share"], experiment["injected"] = shares[experiment["id"]]
    return build_claims(atlas, chosen, summary, projected, acronyms)
