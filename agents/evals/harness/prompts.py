"""Role prompts (agents/roles/): Markdown with a versioned ID in its front matter, read by the harness and the pipeline."""

import re
from pathlib import Path

import yaml

FRONT = re.compile(r"\A---\n(.*?)\n---\n(.*)\Z", re.S)
PROMPT_ID = re.compile(r"^[a-z][a-z0-9_-]*@\d+\.\d+\.\d+$")  # the schema's prompt pattern, such as extract@1.0.0


def read_prompt(path: Path) -> tuple[str, str]:
    """A role prompt's versioned ID (from its front matter) and its text."""
    match = FRONT.match(path.read_text(encoding="utf-8"))
    if not match:
        raise ValueError(f"{path}: a role prompt starts with front matter giving its id, such as id: extract@1.0.0")
    meta = yaml.safe_load(match[1])
    if not isinstance(meta, dict) or not PROMPT_ID.match(str(meta.get("id", ""))):
        raise ValueError(f"{path}: front matter needs an id such as extract@1.0.0")
    return meta["id"], match[2].strip()
