"""Field detection — reading the real fields out of a real document.

The shelf's `pdf_form_filling.read_form_fields` returns each field's real
name and value, which is all the Builder needed. Hands additionally needs
each field's real geometry, because it has to write the completed copy
with every field still in its own place on the page. So this is a real
AcroForm widget reader that returns name, value AND /Rect, and it is
cross-checked in the proof against the shelf reader — two independently
written parsers agreeing about the same real file.

No model is involved in detection, and nothing about a field is inferred:
a field exists here only because it exists in the document's bytes.
"""

import re

from . import config, provenance as prov, shelf

_WIDGET = re.compile(rb"<<[^<>]*?/Subtype\s*/Widget[^<>]*?>>", re.S)
_NAME = re.compile(rb"/T\s*\(((?:\\.|[^()\\])*)\)")
_VALUE = re.compile(rb"/V\s*\(((?:\\.|[^()\\])*)\)")
_RECT = re.compile(rb"/Rect\s*\[\s*([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s*\]")


def _unescape(raw):
    return raw.decode("latin-1").replace(r"\)", ")").replace(r"\(", "(").replace(r"\\", "\\")


def detect(path):
    """Every real text field in the real file, in document order."""
    with open(path, "rb") as handle:
        data = handle.read()

    found = []
    for obj in _WIDGET.findall(data):
        name_m = _NAME.search(obj)
        rect_m = _RECT.search(obj)
        if not name_m or not rect_m:
            continue
        value_m = _VALUE.search(obj)
        name = _unescape(name_m.group(1))
        found.append({
            "name": name,
            "label": name,  # the PDF carries no separate human label; the name is not embellished
            "value": _unescape(value_m.group(1)) if value_m else "",
            "rect": [float(g) for g in rect_m.groups()],
        })
    return found


def classify(detected, known_values=None):
    """Turns detected fields into fields with a provenance.

    A field already carrying a value in the document is KNOWN. A field
    whose value is on file for this customer is KNOWN with that source. A
    field whose name makes a declaration in the customer's name is
    REQUIRES_APPROVAL even when a value is available — that is the
    site-induction rule, applied by field name rather than by category.
    Everything else is MISSING, which is asked for, never guessed.
    """
    known_values = known_values or {}
    out = []
    for field in detected:
        name, value = field["name"], field["value"]
        if config.is_declaration_field(name):
            provenance, source = prov.REQUIRES_APPROVAL, "declaration in the customer's name"
            value = known_values.get(name, value) or ""
            if not value:
                # nothing to declare yet: it is missing first, and gated once supplied
                provenance, source = prov.MISSING, None
        elif value:
            provenance, source = prov.KNOWN, "already present in the uploaded document"
        elif name in known_values and known_values[name]:
            provenance, source, value = prov.KNOWN, "on file for this customer", known_values[name]
        else:
            provenance, source = prov.MISSING, None
        out.append(dict(field, value=value, provenance=provenance, source=source))
    return out


def prove(path=None):
    """Real proof: build a real PDF with real AcroForm fields using the
    shelf part, detect them with this reader, and check the names/values
    match what the shelf's own independent reader sees — plus the rects,
    which only this reader returns."""
    import os
    import tempfile

    made_here = path is None
    if made_here:
        fd, path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
    spec = [
        {"name": "worker_name", "label": "Worker name", "value": "", "rect": [150, 700, 400, 715]},
        {"name": "site_address", "label": "Site address", "value": "12 Rundle St", "rect": [150, 660, 400, 675]},
        {"name": "induction_complete_declaration", "label": "Declaration", "value": "", "rect": [150, 620, 400, 635]},
    ]
    try:
        shelf.pdf_form_filling.render_pdf_with_form(path, "Site induction", spec)
        mine = detect(path)
        theirs = shelf.pdf_form_filling.read_form_fields(path)
        classified = classify(mine, known_values={"worker_name": "Sam Naylor"})
    finally:
        if made_here:
            os.remove(path)

    assert [f["name"] for f in mine] == [f["name"] for f in theirs], "the two parsers disagree on names"
    assert {f["name"]: f["value"] for f in mine} == {f["name"]: f["value"] for f in theirs}
    assert [f["rect"] for f in mine] == [s["rect"] for s in spec], "geometry must survive the round trip"
    by_name = {f["name"]: f for f in classified}
    assert by_name["site_address"]["provenance"] == prov.KNOWN
    assert by_name["worker_name"]["provenance"] == prov.KNOWN
    assert by_name["worker_name"]["value"] == "Sam Naylor"
    assert by_name["induction_complete_declaration"]["provenance"] == prov.MISSING
    return {"part": "document_field_detection",
            "real_system": "a real PDF file on disk, parsed twice by two independently written readers",
            "steps": ["render a real 3-field AcroForm PDF via the shelf part",
                      "detect name/value/rect with this reader",
                      "read name/value with the shelf's own reader",
                      "assert both readers agree, and that the geometry round-trips",
                      "classify: known stays known, a declaration field never auto-fills"],
            "observed": {"detected": mine, "classified": classified}}


if __name__ == "__main__":
    import pprint
    pprint.pprint(prove())
