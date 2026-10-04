"""The screen every full text passes before a model reads it (sprint C.5, ADR 0023).

Three layers, after the plan's Part 3.3 ("limit what a poisoned paper can do"):

1. Invisible characters are stripped; the kinds that can spell out a message are also flagged (invisible.py).
2. JATS elements styled to be invisible are removed and flagged (markup.py).
3. Each paragraph left is scored by a prompt-injection classifier; any at or above its threshold is flagged
   (injection.py).

A flagged paper is never given to a model. Its findings go to the maintainer instead.
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from screen import invisible, jats, markup
from screen.injection import THRESHOLD, Classifier

FIXTURES = Path(__file__).parent / "fixtures"  # planted-*.xml must be flagged, clean-*.xml must not
EXCERPT = 160


@dataclass(frozen=True)
class Finding:
    layer: str  # invisible, hidden-markup or injection
    detail: str
    excerpt: str


@dataclass(frozen=True)
class Screened:
    text: str  # what a model may read: one title or paragraph per line
    findings: tuple[Finding, ...]

    @property
    def flagged(self) -> bool:
        return bool(self.findings)


def _excerpt(text: str) -> str:
    return text if len(text) <= EXCERPT else text[:EXCERPT - 1] + "…"


def _tag_message(text: str) -> str:
    """The ASCII text spelt out by tag characters, which mirror ASCII from U+E0020 to U+E007E."""
    return "".join(chr(ord(c) - 0xE0000) for c in text if 0xE0020 <= ord(c) <= 0xE007E)


def _screen_blocks(raw: list[str], classify: Classifier, findings: list[Finding]) -> Screened:
    kept = []
    for block in raw:
        clean, suspicious = invisible.strip(block)
        clean = " ".join(clean.split())
        if suspicious:
            message = _tag_message(block)
            detail = ", ".join(f"{count} {kind}" for kind, count in sorted(suspicious.items()))
            findings.append(Finding("invisible", detail, _excerpt(f"spells out: {message}" if message else clean)))
        if clean:
            kept.append(clean)
    for block, score in zip(kept, classify(kept) if kept else [], strict=True):
        if score >= THRESHOLD:
            findings.append(Finding("injection", f"score {score:.2f}", _excerpt(block)))
    return Screened("\n".join(kept), tuple(findings))


def screen_text(text: str, classify: Classifier) -> Screened:
    """Plain text, one block per line."""
    return _screen_blocks(text.splitlines(), classify, [])


def screen_jats(xml: bytes, classify: Classifier) -> Screened:
    """A JATS article: hidden elements removed, then its titles and paragraphs screened."""
    root = ET.fromstring(xml)
    findings = [Finding("hidden-markup", reason, _excerpt(text)) for reason, text in markup.strip_hidden(root) if text]
    return _screen_blocks(jats.blocks(root), classify, findings)


def preflight(classify: Classifier) -> list[str]:
    """What the screen gets wrong on its fixtures: a planted hidden prompt it misses, or a clean paper it flags."""
    problems = []
    for path in sorted(FIXTURES.glob("*.xml")):
        result = screen_jats(path.read_bytes(), classify)
        planted = path.name.startswith("planted-")
        if result.flagged != planted:
            seen = "; ".join(f"{f.layer}: {f.detail}" for f in result.findings)
            problems.append(f"{path.name}: {'missed' if planted else 'flagged ' + seen}")
    return problems
