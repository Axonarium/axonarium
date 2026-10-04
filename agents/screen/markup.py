"""JATS elements styled so a reader can't see them: removed before a model reads the text, and flagged.

Europe PMC's JATS keeps a publisher's inline styles in `style` attributes (usually on `styled-content`). Text that is
white, tiny, transparent or not displayed is how hidden prompts are planted in documents (plan, Part 3.3). White text
on a coloured background is ordinary, so colour only counts when no background is set on the element or around it.
"""

import re
import xml.etree.ElementTree as ET

NUMBER = re.compile(r"^(-?[\d.]+)\s*([a-z%]*)$")
RGB = re.compile(r"^rgba?\(\s*([\d.]+%?)\s*[, ]\s*([\d.]+%?)\s*[, ]\s*([\d.]+%?)\s*(?:[,/]\s*([\d.]+%?))?\s*\)$")
TINY = {"": 1, "px": 1, "pt": 1, "em": 0.1, "rem": 0.1, "ex": 0.2, "%": 10}  # at or below these, text can't be read


def declarations(style: str) -> dict[str, str]:
    found = {}
    for part in style.split(";"):
        name, _, value = part.partition(":")
        if value.strip():
            found[name.strip().lower()] = value.strip().lower().removesuffix("!important").strip()
    return found


def _channel(value: str) -> float:
    return float(value[:-1]) * 2.55 if value.endswith("%") else float(value)


def invisible_colour(value: str) -> bool:
    """White, near-white or transparent."""
    if value in ("white", "transparent"):
        return True
    if re.fullmatch(r"#[0-9a-f]{3,8}", value):
        digits = value[1:]
        if len(digits) in (3, 4):
            digits = "".join(d * 2 for d in digits)
        channels = [int(digits[i:i + 2], 16) for i in (0, 2, 4)]
        alpha = int(digits[6:8], 16) / 255 if len(digits) == 8 else 1
        return alpha <= 0.1 or min(channels) >= 240
    match = RGB.match(value)
    if match:
        alpha = match[4]
        if alpha is not None and (_channel(alpha) / 255 if alpha.endswith("%") else float(alpha)) <= 0.1:
            return True
        return min(_channel(c) for c in match.groups()[:3]) >= 240
    return False


def _tiny(value: str) -> bool:
    match = NUMBER.match(value)
    return bool(match) and match[2] in TINY and float(match[1]) <= TINY[match[2]]


def hiding(style: dict[str, str], background: bool) -> str | None:
    """Why this style hides its text, or None."""
    if style.get("display") == "none":
        return "display: none"
    if style.get("visibility") in ("hidden", "collapse"):
        return f"visibility: {style['visibility']}"
    opacity = NUMBER.match(style.get("opacity", ""))
    if opacity and opacity[2] in ("", "%") and float(opacity[1]) / (100 if opacity[2] else 1) <= 0.1:
        return f"opacity: {style['opacity']}"
    if "font-size" in style and _tiny(style["font-size"]):
        return f"font-size: {style['font-size']}"
    if "color" in style and not background and invisible_colour(style["color"]):
        return f"color: {style['color']}"
    return None


def _has_background(style: dict[str, str]) -> bool:
    value = style.get("background-color") or style.get("background")
    return bool(value) and value not in ("none", "transparent", "inherit", "initial") and not invisible_colour(value)


def strip_hidden(root: ET.Element) -> list[tuple[str, str]]:
    """Remove every hidden element (keeping the text that follows it); each one's reason and text."""
    found = []

    def walk(parent: ET.Element, background: bool):
        for child in list(parent):
            style = declarations(child.get("style", ""))
            shaded = background or _has_background(style)
            reason = hiding(style, shaded)
            if reason is None:
                walk(child, shaded)
                continue
            found.append((reason, " ".join("".join(child.itertext()).split())))
            _remove(parent, child)

    walk(root, False)
    return found


def _remove(parent: ET.Element, child: ET.Element):
    """Remove `child`, keeping its tail text in place."""
    children = list(parent)
    index = children.index(child)
    if child.tail:
        if index:
            children[index - 1].tail = (children[index - 1].tail or "") + child.tail
        else:
            parent.text = (parent.text or "") + child.tail
    parent.remove(child)
