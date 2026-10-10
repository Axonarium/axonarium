"""The parts of a JATS article that hold claims (ADR 0028): its title, abstract, methods, results and figure and table
captions. The introduction, discussion, acknowledgements, back matter and references are dropped before the model
reads the paper, since a paper's own results are what it claims; dropping them roughly halves what is sent. So is any
peer-review material published with the paper (eLife's decision letters, reviews and authors' responses), which is
correspondence about the paper, not its findings."""

import re
import xml.etree.ElementTree as ET

from screen.jats import local

DROPPED_TITLES = re.compile(
    r"^\s*(?:[0-9IVX]+[.)]?\s*)?(?:introduction|background|discussion|general discussion|conclusions?|concluding remarks"
    r"|summary and conclusions?|acknowledge?ments?|funding|financial support|author contributions?|contributions"
    r"|competing interests?|conflicts? of interest|declaration of (?:competing )?interests?|disclosures?"
    r"|data availability|code availability|data and code availability|ethics(?: statement)?|supplementary (?:material|data|information)"
    r"|references|abbreviations)\b",
    re.I,
)
DROPPED_TYPES = {"intro", "introduction", "background", "discussion", "conclusion", "conclusions", "acknowledgment",
                 "acknowledgments", "acknowledgement", "acknowledgements", "funding", "supplementary-material",
                 "data-availability", "coi-statement", "author-contributions", "ethics-statement"}
KEPT_FLOATS = {"fig", "table-wrap"}
REVIEW = {"sub-article", "response"}  # JATS's places for the reviews, decision letters and replies printed with a paper


def _title(section: ET.Element) -> str:
    title = next((child for child in section if local(child.tag) == "title"), None)
    return " ".join("".join(title.itertext()).split()) if title is not None else ""


def dropped(section: ET.Element) -> bool:
    kinds = {kind.lower() for kind in (section.get("sec-type") or "").split("|") if kind}
    return bool(kinds & DROPPED_TYPES) or bool(DROPPED_TITLES.match(_title(section)))


def _floats(element: ET.Element) -> list[ET.Element]:
    """The figures and tables inside an element, outermost only."""
    found = []
    for child in element:
        if local(child.tag) in KEPT_FLOATS:
            found.append(child)
        else:
            found += _floats(child)
    return found


def prune(root: ET.Element) -> None:
    """Drop the sections that hold no claims, and all back matter, keeping any figures and tables they contain; and
    the peer-review material, figures and all."""

    def walk(element: ET.Element):
        for child in list(element):
            tag = local(child.tag)
            if tag in REVIEW:
                element.remove(child)
            elif tag == "back" or (tag == "sec" and dropped(child)):
                kept = _floats(child)
                element.remove(child)
                element.extend(kept)
            else:
                walk(child)

    walk(root)
