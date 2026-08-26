"""ASCII slug helper. Polish diacritics folded to their base letters."""

from __future__ import annotations

import re

_FOLD = str.maketrans(
    {
        "ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n", "ó": "o",
        "ś": "s", "ź": "z", "ż": "z",
        "Ą": "a", "Ć": "c", "Ę": "e", "Ł": "l", "Ń": "n", "Ó": "o",
        "Ś": "s", "Ź": "z", "Ż": "z",
    }
)


def slugify(text: str, *, maxlen: int = 120) -> str:
    s = text.strip().lower().translate(_FOLD)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:maxlen].rstrip("-")
