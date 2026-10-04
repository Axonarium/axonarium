"""Invisible characters: stripped from everything a model reads, and flagged when they can carry a hidden message.

The rule is LLM Guard's InvisibleText scanner's: a character in Unicode's format (Cf), private-use (Co) or unassigned
(Cn) categories is invisible. LLM Guard itself would bring PyTorch for these few lines, so the rule is applied with the
standard library (ADR 0023). Variation selectors (Mn) are added, because a run of them can encode bytes too.

Papers legitimately hold some invisible characters: soft hyphens, zero-width spaces, invisible maths operators, a
publisher's private-use glyphs, the selector after an emoji. Those are stripped without a flag. The kinds that can spell
out a hidden instruction are flagged as well.
"""

import unicodedata

INVISIBLE = {"Cf", "Co", "Cn"}
VARIATION_SELECTORS = (range(0xFE00, 0xFE10), range(0xE0100, 0xE01F0))

# Flagged as well as stripped: each can carry text that a human never sees.
SUSPICIOUS = {
    "tag characters": range(0xE0000, 0xE0080),  # "ASCII smuggling": each tag character mirrors an ASCII one
    "bidirectional overrides": range(0x202A, 0x202F),  # reorder what is displayed ("Trojan Source")
    "bidirectional isolates": range(0x2066, 0x206A),
    "supplementary variation selectors": range(0xE0100, 0xE01F0),  # with FE00–FE0F, one selector per hidden byte
}


def kind(char: str) -> str | None:
    """Which suspicious kind an invisible character is, '' for a harmless invisible one, None if it is visible."""
    point = ord(char)
    category = unicodedata.category(char)
    if category not in INVISIBLE and not any(point in r for r in VARIATION_SELECTORS):
        return None
    if category == "Cn":
        return "unassigned code points"
    return next((name for name, points in SUSPICIOUS.items() if point in points), "")


def strip(text: str) -> tuple[str, dict[str, int]]:
    """The text without invisible characters, and how many suspicious ones of each kind it held."""
    kept, counts = [], {}
    for char in text:
        found = kind(char)
        if found is None:
            kept.append(char)
        elif found:
            counts[found] = counts.get(found, 0) + 1
    return "".join(kept), counts
