"""Which atlas regions and UBERON terms belong to each module (ADR 0031), from data/modules.yaml and the atlases.

A module names UBERON roots, regions to include and regions or terms to exclude. An atlas region belongs when its
UBERON term is a root or under one, or when it is included; its subdivisions belong with it. Excluding an atlas
region removes it and its subdivisions; excluding a UBERON term removes the term and the atlas regions mapped to it,
with theirs. A UBERON term belongs when it is a root or under one, is included, or is the term of a member region.
"""

from collections import defaultdict

from checks.findings import Record


def modules_of(records: list[Record]) -> list[dict]:
    """The modules of data/modules.yaml, in its order; none without the file."""
    return next((list(r.data.get("modules") or []) for r in records if r.cls == "ModuleList"), [])


def roots_of(modules: list[dict]) -> list[str]:
    """Every UBERON root the modules name, in order, once each."""
    return list(dict.fromkeys(root for module in modules for root in module.get("roots") or []))


def _subtrees(rows: list[dict]) -> dict[str, list[str]]:
    children: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        if row["parent"]:
            children[row["parent"]].append(row["id"])
    return children


def _with_subdivisions(seeds: set[str], children: dict[str, list[str]]) -> set[str]:
    found, stack = set(), list(seeds)
    while stack:
        region = stack.pop()
        if region not in found:
            found.add(region)
            stack.extend(children.get(region, []))
    return found


def resolve(modules: list[dict], rows: list[dict], terms: dict[str, dict[str, str]]) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """(per atlas region ID, the modules it belongs to; per module, the UBERON terms that belong to it), for the
    region rows of every loaded atlas. `terms` maps each root to the terms under it (ingest.atlases.descendant_terms)."""
    children = _subtrees(rows)
    members: dict[str, list[str]] = defaultdict(list)
    module_terms: dict[str, list[str]] = {}
    for module in modules:
        include, exclude = set(module.get("include") or []), set(module.get("exclude") or [])
        under = {term for root in module.get("roots") or [] for term in terms.get(root, {root: ""})}
        wanted_terms = (under | {i for i in include if i.startswith("UBERON:")}) - exclude
        seeds = {row["id"] for row in rows if row["uberon"] in wanted_terms or row["id"] in include}
        dropped = {row["id"] for row in rows if row["id"] in exclude or row["uberon"] in exclude}
        regions = _with_subdivisions(seeds, children) - _with_subdivisions(dropped, children)
        for region in regions:
            members[region].append(module["id"])
        mapped = {row["uberon"] for row in rows if row["id"] in regions and row["uberon"]} - exclude
        module_terms[module["id"]] = sorted(wanted_terms | mapped)
    return dict(members), module_terms


def apply(modules: list[dict], loaded: dict[str, list[dict]], terms: dict[str, dict[str, str]]) -> dict[str, list[str]]:
    """Set each loaded region row's `modules` (in the file's order, or None for none) and return each module's
    UBERON terms."""
    rows = [row for found in loaded.values() for row in found]
    members, module_terms = resolve(modules, rows, terms)
    for row in rows:
        row["modules"] = members.get(row["id"]) or None
    return module_terms


def structures(rows: list[dict], module: str | None = None) -> list[int]:
    """The Allen structure IDs of one module's regions, or of every module's, from an atlas's region rows (after
    `apply`)."""
    return sorted(int(row["id"].split(":")[1]) for row in rows
                  if row.get("modules") and (module is None or module in row["modules"]))
