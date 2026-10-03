"""Finding and loading data files, and the layout that decides their class and file name."""

from pathlib import Path

import yaml

from checks.findings import Finding, Record
from checks.identifiers import source_file_name

IGNORED = {Path("allowlist.yaml")}  # Reserved for sprint C.2.


class DuplicateKeyError(yaml.YAMLError):
    pass


def parse_yaml(text: str):
    """Parse one YAML document safely: no repeated keys, no anchors or aliases."""
    for event in yaml.parse(text, Loader=yaml.SafeLoader):
        if isinstance(event, yaml.AliasEvent) or getattr(event, "anchor", None):
            raise yaml.YAMLError("anchors and aliases are not allowed in data files")
    return yaml.load(text, Loader=UniqueKeyLoader)


class UniqueKeyLoader(yaml.SafeLoader):
    """A safe loader that rejects repeated keys, which YAML would otherwise silently overwrite."""

    def construct_mapping(self, node, deep=False):
        seen = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in seen:
                raise DuplicateKeyError(f"key {key!r} appears more than once (line {key_node.start_mark.line + 1})")
            seen.add(key)
        return super().construct_mapping(node, deep)


def class_for(rel_path: Path) -> str | None:
    """The schema class a file holds, from its folder under data/; None if the folder isn't a data folder."""
    parts = rel_path.parts
    if rel_path.suffix != ".yaml":
        return None
    if parts == ("retractions.yaml",):
        return "RetractionLog"
    if parts[0] == "claims" and len(parts) >= 2:
        return "ConnectivityClaim"
    if parts[0] == "homology" and len(parts) >= 2:
        return "HomologyClaim"
    if parts[0] == "sources" and len(parts) >= 2:
        return "Source"
    if parts[:2] == ("entities", "atlases") and len(parts) == 3:
        return "Atlas"
    if parts[:2] == ("entities", "regions") and len(parts) >= 3:
        return "Region"
    if parts[:2] == ("entities", "neuron_types") and len(parts) == 3:
        return "NeuronType"
    return None


def expected_file_name(cls: str, record_id: str) -> str | None:
    """The file name a record must have, or None where the name is free."""
    if cls in ("ConnectivityClaim", "HomologyClaim", "Atlas", "NeuronType"):
        return f"{record_id}.yaml"
    if cls == "Region":
        return f"{record_id.replace(':', '_')}.yaml"
    if cls == "Source" and ":" in record_id:
        return source_file_name(record_id)
    return None


def load_tree(data_dir: Path) -> tuple[list[Record], list[Finding]]:
    """Every YAML file under data_dir, loaded; problems that stop a file from being checked further."""
    records, findings = [], []
    for path in sorted(data_dir.rglob("*")):
        if path.is_symlink():
            findings.append(Finding(str(path), "symlink", "data files must be real files, not symbolic links"))
            continue
        if not (path.is_file() and path.suffix in (".yaml", ".yml")):
            continue
        rel = path.relative_to(data_dir)
        if rel in IGNORED:
            continue
        cls = class_for(rel)
        if cls is None:
            findings.append(Finding(str(path), "unknown-location", "not in a data folder; see data/README.md"))
            continue
        try:
            data = parse_yaml(path.read_text(encoding="utf-8"))
        except DuplicateKeyError as error:
            findings.append(Finding(str(path), "duplicate-key", str(error)))
            continue
        except (yaml.YAMLError, UnicodeDecodeError, TypeError, ValueError, RecursionError) as error:
            findings.append(Finding(str(path), "yaml-error", " ".join(str(error).split())[:300]))
            continue
        if not isinstance(data, dict):
            findings.append(Finding(str(path), "yaml-error", "the top level must be a mapping"))
            continue
        records.append(Record(path, cls, data))
    return records, findings
