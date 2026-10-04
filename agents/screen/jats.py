"""What a model reads of a JATS article: its titles and paragraphs, one block per line, references left out."""

import xml.etree.ElementTree as ET

BLOCKS = {"article-title", "title", "p"}
SKIP = {"ref-list"}  # the titles of cited papers, not this paper's text


def local(tag) -> str:
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def blocks(root: ET.Element) -> list[str]:
    """Each title and paragraph's raw text, in document order. A paragraph inside another block stays part of it."""
    found = []

    def walk(element: ET.Element):
        for child in element:
            tag = local(child.tag)
            if tag in SKIP:
                continue
            if tag in BLOCKS:
                found.append("".join(child.itertext()))
            else:
                walk(child)

    walk(root)
    return found
