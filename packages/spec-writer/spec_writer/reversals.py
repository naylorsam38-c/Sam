from __future__ import annotations

import re
from typing import Iterable


def parse_turns(transcript: str) -> list[tuple[str, str]]:
    """
    Parse common speaker-labelled transcripts.

    Accepted:
      Sam: ...
      Nova: ...
      [12] Sam: ...
      12 | Sam | ...
    Unrecognised lines are retained as continuation text.
    """
    turns = []
    current = None

    patterns = [
        re.compile(r"^\s*\[(\d+)\]\s*([^:|]+)\s*:\s*(.*)$"),
        re.compile(r"^\s*(\d+)\s*\|\s*([^|]+)\s*\|\s*(.*)$"),
        re.compile(r"^\s*([^:|]+)\s*:\s*(.*)$"),
    ]

    for line in transcript.splitlines():
        match = None
        for i, pattern in enumerate(patterns):
            m = pattern.match(line)
            if m:
                match = m
                if i == 0:
                    turn_no, speaker, text = m.groups()
                elif i == 1:
                    turn_no, speaker, text = m.groups()
                else:
                    turn_no = str(len(turns) + 1)
                    speaker, text = m.groups()
                current = [int(turn_no), speaker.strip(), text]
                turns.append(current)
                break
        if match is None and current is not None:
            current[2] += "\n" + line

    return [(f"{n}", speaker, text) for n, speaker, text in turns]


def reversal_contract() -> str:
    return (
        "If the transcript contains a reversal, only the later position is "
        "authoritative. The earlier position MUST NOT be carried into the "
        "extracted intent. Record the dropped turn number separately."
    )
