"""
Phrase chunker (spec §4). Splits a streaming token flow into ~4–12 word phrases
on natural boundaries so TTS can start speaking before the full answer arrives.
"""
from __future__ import annotations

import re

_BOUNDARY = re.compile(r"[.!?,;:—]\s|\n")
MIN_WORDS, MAX_WORDS = 4, 12


class PhraseChunker:
    def __init__(self) -> None:
        self._buf = ""

    def feed(self, token: str) -> list[str]:
        """Add streamed text; return any complete phrases now ready to speak."""
        self._buf += token
        out: list[str] = []
        while True:
            phrase = self._try_cut()
            if phrase is None:
                break
            out.append(phrase)
        return out

    def _try_cut(self) -> str | None:
        words = self._buf.split()
        if len(words) < MIN_WORDS:
            return None
        # cut at first natural boundary at/after MIN_WORDS
        m = _BOUNDARY.search(self._buf)
        if m and len(self._buf[:m.end()].split()) >= MIN_WORDS:
            cut = self._buf[:m.end()].strip()
            self._buf = self._buf[m.end():]
            return cut
        # force a cut if we've buffered too many words
        if len(words) >= MAX_WORDS:
            cut = " ".join(words[:MAX_WORDS])
            self._buf = " ".join(words[MAX_WORDS:])
            return cut
        return None

    def flush(self) -> str | None:
        """Emit whatever remains at end-of-turn."""
        rest, self._buf = self._buf.strip(), ""
        return rest or None
