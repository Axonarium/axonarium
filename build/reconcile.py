"""The reconciliation report (sprint 1.6): where sources agree, conflict or are silent about a connection.

It reports and never resolves (plan, Agent operating model: the Reconciler never resolves conflicts by majority
vote). A source is a cited paper or dataset (a claim's source key), grouped for display by how its claims came in:
an ingester's adapter, such as allen-connectivity, or the literature. An observation is one experiment or figure
(a source and locator). The report holds build-time Allen claims, so it is published with CI's runs and never
committed (ADR 0005).
"""

import io
import json
from collections import defaultdict
from pathlib import Path

from build.connectivity import amygdala_regions

THRESHOLDS = (0.01, 0.02, 0.05, 0.1, 0.2)  # projection densities; the Allen claims start at 0.01 (ADR 0010)
CATEGORIES = ("agreement", "conflict", "replicated", "single")
LABELS = {"agreement": "Agreement", "conflict": "Conflict", "replicated": "Replicated", "single": "One observation"}
MEANINGS = {
    "agreement": "Two or more sources, none contradicting another",
    "conflict": "One finds the connection, another tested it and didn't",
    "replicated": "One source, two or more experiments or figures",
    "single": "One source, one experiment or figure",
}
SHOWN_CONFLICTS = 50


def _group(claim: dict) -> str:
    """How a claim came in: its adapter (its procedure's name) for an ingester, else the literature."""
    curation = claim.get("curation") or {}
    if curation.get("role") == "ingester" and isinstance(curation.get("prompt"), str):
        return curation["prompt"].split("@")[0]
    return "literature"


def _source(claim: dict) -> str:
    cited = claim["source"]
    return next(f"{k}:{cited[k]}".lower() for k in ("doi", "pmid", "pmcid", "arxiv") if cited.get(k))


def _connection(claim: dict) -> str:
    return "|".join((claim["subject"]["id"], claim["predicate"], claim["object"]["id"], claim["species"]))


def _density(claim: dict) -> float | None:
    values = [m["value"] for m in claim.get("measurements") or [] if m.get("quantity") == "projection_density"]
    return max(values) if values else None


def _category(claims: list[dict]) -> str:
    results = {c["result"] for c in claims}
    if {"present", "absent"} <= results:
        return "conflict"
    if len({_source(c) for c in claims}) > 1:
        return "agreement"
    return "replicated" if len({(_source(c), c["source"].get("locator")) for c in claims}) > 1 else "single"


def _direction(claim: dict, amygdala: set[str]) -> str:
    if claim["subject"]["id"] in amygdala:
        return "outputs"
    return "inputs" if claim["object"]["id"] in amygdala else "other"


def _thresholds(connections: dict[str, list[dict]]) -> list[dict]:
    rows = []
    for minimum in THRESHOLDS:
        strong = [[c for c in claims if c["result"] == "present" and (_density(c) or 0) >= minimum] for claims in connections.values()]
        rows.append({"min": minimum, "connections": sum(bool(s) for s in strong),
                     "replicated": sum(len({(_source(c), c["source"].get("locator")) for c in s}) > 1 for s in strong)})
    return rows


def reconcile(claims: list[dict], regions: list[dict]) -> dict:
    """The report for these connectivity claims (committed and build-time); `regions` are the atlases' regions."""
    live = [c for c in claims if c.get("status") != "retracted"]
    amygdala = amygdala_regions(regions)
    connections: dict[str, list[dict]] = defaultdict(list)
    for claim in live:
        connections[_connection(claim)].append(claim)
    categories = {key: _category(found) for key, found in connections.items()}

    sources = []
    for group in sorted({_group(c) for c in live}):
        mine = [c for c in live if _group(c) == group]
        sources.append({"name": group, "claims": len(mine), "connections": len({_connection(c) for c in mine}),
                        "observations": len({(_source(c), c["source"].get("locator")) for c in mine})})

    by_direction: dict[str, dict[str, int]] = {d: dict.fromkeys(CATEGORIES, 0) for d in ("outputs", "inputs", "other")}
    for key, found in connections.items():
        by_direction[_direction(found[0], amygdala)][categories[key]] += 1

    conflicts = [{"connection": key, "results": {group: sorted({c["result"] for c in found if _group(c) == group})
                                                 for group in sorted({_group(c) for c in found})}}
                 for key, found in sorted(connections.items()) if categories[key] == "conflict"]

    silence = None
    if amygdala:
        acronym = {row["id"]: row.get("acronym") or row["id"] for row in regions}
        subjects = {c["subject"]["id"] for c in live}
        objects = {c["object"]["id"] for c in live}
        names = lambda ids: sorted(acronym[i] for i in ids)  # noqa: E731
        silence = {"amygdala_regions": len(amygdala), "without_outputs": names(amygdala - subjects),
                   "without_inputs": names(amygdala - objects), "without_either": names(amygdala - subjects - objects)}

    by_side = {side: {k: v for k, v in connections.items() if _direction(v[0], amygdala) == side} for side in ("outputs", "inputs")}
    return {
        "connections": len(connections),
        "categories": {name: sum(c == name for c in categories.values()) for name in CATEGORIES},
        "sources": sources,
        "by_direction": by_direction,
        "conflicts": conflicts,
        "thresholds": {side: _thresholds(found) for side, found in by_side.items()},
        "silence": silence,
    }


def _markdown(report: dict) -> str:
    lines = ["# Reconciliation", "",
             "Where sources agree, conflict or are silent about a connection (sprint 1.6). Conflicts are reported, "
             "never resolved. Made by `python -m build --report`.", "",
             f"{report['connections']} connections, from:", "",
             "| Source | Claims | Connections | Experiments or figures |", "| --- | --- | --- | --- |"]
    lines += [f"| {s['name']} | {s['claims']} | {s['connections']} | {s['observations']} |" for s in report["sources"]]
    lines += ["", "## Agreement", "", "| Connections | Count | Meaning |", "| --- | --- | --- |"]
    lines += [f"| {LABELS[c]} | {report['categories'][c]} | {MEANINGS[c]} |" for c in CATEGORIES]
    lines += ["", "| Amygdala's | " + " | ".join(LABELS[c] for c in CATEGORIES) + " |", "| --- |" + " --- |" * len(CATEGORIES)]
    lines += [f"| {side} | " + " | ".join(str(n[c]) for c in CATEGORIES) + " |" for side, n in report["by_direction"].items()]
    lines += ["", "## Conflicts", ""]
    if report["conflicts"]:
        lines += [f"- `{c['connection']}`: " + "; ".join(f"{g} {', '.join(r)}" for g, r in c["results"].items())
                  for c in report["conflicts"][:SHOWN_CONFLICTS]]
        if len(report["conflicts"]) > SHOWN_CONFLICTS:
            lines.append(f"- … and {len(report['conflicts']) - SHOWN_CONFLICTS} more in reconciliation.json")
    else:
        lines.append("None.")
    lines += ["", "## Projection density thresholds", "",
              "Connections whose strongest claim reaches each density, and those reaching it in two or more experiments. "
              "Low input densities may be fibres of passage rather than terminals (ADR 0010).", "",
              "| At least | Outputs | Replicated | Inputs | Replicated |", "| --- | --- | --- | --- | --- |"]
    for out, into in zip(report["thresholds"]["outputs"], report["thresholds"]["inputs"]):
        lines.append(f"| {out['min']} | {out['connections']} | {out['replicated']} | {into['connections']} | {into['replicated']} |")
    lines += ["", "## Silence", ""]
    silence = report["silence"]
    if silence is None:
        lines.append("Not computed: the build ran without atlases.")
    else:
        lines += [f"Of {silence['amygdala_regions']} amygdala regions and subdivisions:", "",
                  f"- No claim names any of these: {', '.join(silence['without_either']) or 'none'}.",
                  f"- No outputs measured from: {', '.join(silence['without_outputs']) or 'none'}.",
                  f"- No inputs found into: {', '.join(silence['without_inputs']) or 'none'}."]
    return "\n".join(lines) + "\n"


def _figure(report: dict) -> str:
    import matplotlib

    matplotlib.use("svg")
    import matplotlib.pyplot as plt

    matplotlib.rcParams["svg.hashsalt"] = "axonarium"  # stable element IDs, so the same report gives the same file
    figure, (left, right) = plt.subplots(1, 2, figsize=(11, 4.2), layout="constrained")
    sides = list(report["by_direction"])
    bottom = [0] * len(sides)
    for category, colour in zip(CATEGORIES, ("#2a9d8f", "#e76f51", "#457b9d", "#a8dadc")):
        heights = [report["by_direction"][s][category] for s in sides]
        left.bar(sides, heights, bottom=bottom, label=LABELS[category], color=colour)
        bottom = [b + h for b, h in zip(bottom, heights)]
    left.set_title("Connections by agreement between sources")
    left.set_ylabel("Connections")
    left.legend(frameon=False)
    for side, colour in (("outputs", "#264653"), ("inputs", "#e9c46a")):
        rows = report["thresholds"][side]
        x = [r["min"] for r in rows]
        right.plot(x, [r["connections"] for r in rows], marker="o", color=colour, label=f"{side}")
        right.plot(x, [r["replicated"] for r in rows], marker="o", linestyle="--", color=colour, label=f"{side}, ≥2 experiments")
    right.set_xscale("log")
    right.set_xticks(THRESHOLDS, [str(t) for t in THRESHOLDS])
    right.set_title("Connections at or above a projection density")
    right.set_xlabel("Projection density")
    right.legend(frameon=False)
    buffer = io.StringIO()
    figure.savefig(buffer, format="svg", metadata={"Date": None})
    plt.close(figure)
    return buffer.getvalue()


def write_report(report: dict, out: Path) -> None:
    """reconciliation.json, .md and .svg in `out`."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "reconciliation.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (out / "reconciliation.md").write_text(_markdown(report), encoding="utf-8")
    (out / "reconciliation.svg").write_text(_figure(report), encoding="utf-8")
