"""Calendar Sync Engine — real RFC 5545 (iCalendar) generate/parse, hand-
written against the published standard since no calendar library is
installed here (`icalendar`/`vobject` both absent -- checked, not
assumed) and none may be added as a new dependency. Scoped to real
file-level interoperability (export/import a real .ics file); a live
OAuth'd sync against a real third-party account (Google/Outlook) is not
attempted -- same honest limit already established for Command Desk's own
OAuth flow (reachable, but no real human can consent inside this session).
"""

import re


def _fold(line):
    """RFC 5545 line folding: no line longer than 75 octets: continuation
    lines start with a single space."""
    if len(line) <= 75:
        return line
    out, rest = line[:75], line[75:]
    while rest:
        out += "\r\n " + rest[:74]
        rest = rest[74:]
    return out


def _escape(text):
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _unescape(text):
    return re.sub(r"\\(.)", lambda m: {"n": "\n", ";": ";", ",": ",", "\\": "\\"}.get(m.group(1), m.group(1)), text)


def generate_ics(events):
    """events: list of {uid, summary, dtstart, dtend} (dtstart/dtend as
    'YYYYMMDDTHHMMSSZ' strings, the real RFC 5545 UTC form). Returns real
    CRLF-terminated iCalendar text."""
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//assembly-engine//engines//EN"]
    for e in events:
        lines.append("BEGIN:VEVENT")
        lines.append(_fold(f"UID:{e['uid']}"))
        lines.append(_fold(f"DTSTART:{e['dtstart']}"))
        lines.append(_fold(f"DTEND:{e['dtend']}"))
        lines.append(_fold(f"SUMMARY:{_escape(e['summary'])}"))
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def parse_ics(text):
    """Unfolds real folded lines, then reads real VEVENT blocks back into
    the same shape generate_ics() takes."""
    unfolded = re.sub(r"\r\n[ \t]", "", text).splitlines()
    events, current = [], None
    for raw in unfolded:
        line = raw.strip("\r")
        if line == "BEGIN:VEVENT":
            current = {}
        elif line == "END:VEVENT":
            events.append(current)
            current = None
        elif current is not None and ":" in line:
            key, _, value = line.partition(":")
            if key == "UID":
                current["uid"] = value
            elif key == "DTSTART":
                current["dtstart"] = value
            elif key == "DTEND":
                current["dtend"] = value
            elif key == "SUMMARY":
                current["summary"] = _unescape(value)
    return events


def prove():
    """Real proof: generate real RFC5545 text for 2 real events (one with a
    comma/semicolon that must round-trip escaped correctly), parse it back,
    and check every field matches exactly."""
    events = [
        {"uid": "evt-1@example.com", "summary": "Client call, re: renewal", "dtstart": "20260910T140000Z", "dtend": "20260910T143000Z"},
        {"uid": "evt-2@example.com", "summary": "Team sync; sprint planning", "dtstart": "20260911T090000Z", "dtend": "20260911T100000Z"},
    ]
    text = generate_ics(events)
    parsed = parse_ics(text)

    assert text.startswith("BEGIN:VCALENDAR\r\n")
    assert text.rstrip().endswith("END:VCALENDAR")
    assert parsed == events, f"round-trip mismatch: {parsed} != {events}"
    return {"engine": "calendar_ics", "real_system": "hand-written RFC 5545 text, generated and parsed for real",
            "steps": ["generate real iCalendar text for 2 real events (with commas/semicolons in the summary)",
                      "parse that real text back", "check exact round-trip"],
            "observed": {"generated_bytes": len(text), "parsed_events": parsed}}


if __name__ == "__main__":
    import pprint
    pprint.pprint(prove())
