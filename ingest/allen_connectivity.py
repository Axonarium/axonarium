"""Region-level connectivity claims from the Allen Mouse Brain Connectivity Atlas, made at build time (ADR 0010).

Allen terms allow non-commercial use but not commercial redistribution, so these claims are never committed and
never dumped (ADR 0005); the live site shows them with the citation. Each claim is one experiment's projection
into one target, from wild-type mice with the primary injection in the amygdala.
"""

import hashlib
from collections.abc import Callable
from urllib.parse import quote

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

API = "https://api.brain-map.org/api/v2/data/query.json?criteria={criteria}&num_rows={num_rows}"
PROJECTION_PRODUCT = 5  # Mouse Connectivity: Projection
SUMMARY_STRUCTURES = 167587189  # "Brain – Summary Structures", the 316 targets Allen's own analyses use
DENSITY_MIN = 0.01
SHARE_MIN = 0.5  # Below this share of the injection in the primary structure, claims are proposed, not accepted.
SOURCE = {"doi": "10.1038/nature13186"}  # Oh et al. 2014, "A mesoscale connectome of the mouse brain"
# Ingesters are agents without a language model: `model` says so, and `prompt` is the adapter's versioned procedure.
# Bump the version whenever the adapter's output changes; it and the date keep reruns identical (ADR 0010).
MODEL = "deterministic-adapter"
PROCEDURE = "allen-connectivity@1.1.0"
ADAPTER_DATE = "2026-10-03"
CROCKFORD = "0123456789abcdefghjkmnpqrstvwxyz"
USER_AGENT = {"User-Agent": "axonarium-build (https://github.com/axonarium/axonarium)"}


def _session() -> requests.Session:
    session = requests.Session()
    retry = Retry(total=4, backoff_factor=1, status_forcelist=(429, 500, 502, 503, 504), allowed_methods=("GET",))
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update(USER_AGENT)
    return session


def _get(criteria: str, num_rows: int = 2000, session: requests.Session | None = None) -> list[dict]:
    """The rows an Allen API RMA query returns; an unsuccessful query is an error."""
    response = (session or _session()).get(API.format(criteria=quote(criteria, safe="[]$:,'()="), num_rows=num_rows), timeout=120)
    response.raise_for_status()
    body = response.json()
    if not body.get("success"):
        raise RuntimeError(f"Allen API query failed: {str(body.get('msg'))[:200]}")
    return body["msg"]


def claim_id(experiment: int, target: int) -> str:
    """A stable claim ID: the same experiment and target always give the same ID (ADR 0004's shape)."""
    number = int.from_bytes(hashlib.sha256(f"allen-connectivity:{experiment}:{target}".encode()).digest()[:8], "big")
    return "clm-" + "".join(CROCKFORD[(number >> (5 * i)) & 31] for i in range(10))


def experiments(get: Callable, structure_ids: list[int]) -> list[dict]:
    """Wild-type projection experiments that passed QC, with the primary injection in one of these structures."""
    criteria = (f"model::SectionDataSet,rma::criteria,[failed$eqfalse],products[id$eq{PROJECTION_PRODUCT}],"
                f"specimen(stereotaxic_injections[primary_injection_structure_id$in{','.join(map(str, sorted(structure_ids)))}]),"
                "rma::include,specimen(donor(transgenic_lines)),specimen(stereotaxic_injections(primary_injection_structure))")
    found = []
    for row in get(criteria, 2000):
        specimen = row["specimen"]
        if specimen["donor"].get("transgenic_lines"):
            continue  # Cre lines label cell types: neuron-type claims, a later sprint.
        injection = specimen["stereotaxic_injections"][0]["primary_injection_structure"]
        found.append({"id": row["id"], "injection": injection["id"]})
    return sorted(found, key=lambda e: e["id"])


def summary_structures(get: Callable) -> set[int]:
    return {row["id"] for row in get(f"model::Structure,rma::criteria,structure_sets[id$eq{SUMMARY_STRUCTURES}]", 2000)}


def injection(get: Callable, experiment: int, summary: set[int], primary: int) -> tuple[float, set[int]]:
    """The primary structure's share of the injected volume, and every summary structure that received tracer."""
    rows = get(f"model::ProjectionStructureUnionize,rma::criteria,[section_data_set_id$eq{experiment}],"
               "[is_injection$eqtrue],[hemisphere_id$eq3]", 2000)
    volumes = {r["structure_id"]: r["projection_volume"] for r in rows if r["structure_id"] in summary and r["projection_volume"] > 0}
    total = sum(volumes.values())
    return (volumes.get(primary, 0) / total if total else 0.0), set(volumes)


def projections(get: Callable, experiment: int) -> list[dict]:
    """Projection density per structure, both hemispheres, outside the injection site."""
    return get(f"model::ProjectionStructureUnionize,rma::criteria,[section_data_set_id$eq{experiment}],"
               "[is_injection$eqfalse],[hemisphere_id$eq3]", 2000)


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
    """The claims for wild-type injections into these structures (the amygdala and its subdivisions)."""
    if not structure_ids:
        return []
    if get is None:
        session = _session()
        get = lambda criteria, num_rows=2000: _get(criteria, num_rows, session)  # noqa: E731
    found = experiments(get, structure_ids)
    summary = summary_structures(get)
    for experiment in found:
        experiment["share"], experiment["injected"] = injection(get, experiment["id"], summary, experiment["injection"])
    projected = {experiment["id"]: projections(get, experiment["id"]) for experiment in found}
    return build_claims(atlas, found, summary, projected, acronyms)
