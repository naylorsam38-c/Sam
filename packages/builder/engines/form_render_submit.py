"""Form Render & Submit Engine — turns a record's own declared fields into
a real HTML form, and turns that form's real submission into a real row.

Until now the Builder had a rule for list and detail screens but none for a
form screen, so every `screen/form` and every `action/submit` in every
locked template was UNBOUND. This is that rule.

Nothing about a form is invented here: the controls, their types, and which
are required come from the record's own R.02 answer, and a submitted value
for a field the record does not declare is refused rather than stored.
"""

import html
import re
import sqlite3

#: graph field type -> the real HTML control that collects it
CONTROLS = {
    "short_text": ("input", "text"), "long_text": ("textarea", None),
    "whole_number": ("input", "number"), "decimal_number": ("input", "number"),
    "money": ("input", "number"), "date": ("input", "date"),
    "date_time": ("input", "datetime-local"), "yes_no": ("input", "checkbox"),
    "one_choice": ("select", None), "multi_choice": ("select", None),
    "email": ("input", "email"), "phone": ("input", "tel"),
    "url": ("input", "url"), "file": ("input", "file"),
    "link": ("select", None), "other": ("input", "text"),
}


class FieldNotDeclared(ValueError):
    """A submitted value for something the record does not declare."""


class MissingRequired(ValueError):
    pass


class NotUnique(ValueError):
    pass


def _slug(name):
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def render_form(record, fields, action_url, link_options=None):
    """A real, self-contained HTML form: one labelled control per declared
    field, `required` on the ones the record says are required, and the
    record's own name as the legend."""
    link_options = link_options or {}
    parts = [f'<form method="post" action="{html.escape(action_url)}" data-record="{html.escape(record)}">',
             f"<h1>{html.escape(record)}</h1>"]
    for field in fields:
        key = _slug(field["name"])
        tag, input_type = CONTROLS[field["type"]]
        required = ' required' if field.get("required") == "yes" else ""
        label = html.escape(field["name"])
        parts.append(f'<label for="{key}">{label}</label>')
        if tag == "textarea":
            parts.append(f'<textarea id="{key}" name="{key}"{required}></textarea>')
        elif tag == "select":
            options = field.get("options") or link_options.get(field["name"]) or []
            multiple = " multiple" if field["type"] == "multi_choice" else ""
            rendered = "".join(f'<option value="{html.escape(str(o))}">{html.escape(str(o))}</option>'
                               for o in options)
            parts.append(f'<select id="{key}" name="{key}"{multiple}{required}>{rendered}</select>')
        else:
            parts.append(f'<input id="{key}" name="{key}" type="{input_type}"{required}>')
    parts.append('<button type="submit">Save</button></form>')
    return "\n".join(parts)


def read_back(form_html):
    """Parses rendered form HTML with the stdlib parser and returns
    ({control id: its type}, {ids marked required}). Independent of the
    renderer above, so agreement between the two means something."""
    from html.parser import HTMLParser

    class Reader(HTMLParser):
        def __init__(self):
            super().__init__()
            self.controls = {}
            self.required = set()

        def handle_starttag(self, tag, attrs):
            if tag not in ("input", "textarea", "select"):
                return
            attributes = dict(attrs)
            key = attributes.get("id")
            if not key:
                return
            self.controls[key] = attributes.get("type") or tag
            if "required" in attributes:
                self.required.add(key)

    reader = Reader()
    reader.feed(form_html)
    return reader.controls, reader.required


def validate(fields, values):
    """Checks a real submission against the record's own declared fields.
    Returns the values keyed by real column name."""
    declared = {_slug(f["name"]): f for f in fields}
    unknown = sorted(set(values) - set(declared))
    if unknown:
        raise FieldNotDeclared(f"{unknown} is not a field of this record: {sorted(declared)}")

    cleaned = {}
    for key, field in declared.items():
        raw = values.get(key)
        if field["type"] == "yes_no":
            cleaned[key] = 1 if raw in (True, "on", "1", "yes", 1) else 0
            continue
        if raw in (None, ""):
            if field.get("required") == "yes":
                raise MissingRequired(f"{field['name']} is required")
            cleaned[key] = None
            continue
        if field["type"] in ("whole_number", "decimal_number", "money"):
            try:
                cleaned[key] = int(raw) if field["type"] == "whole_number" else float(raw)
            except (TypeError, ValueError):
                raise MissingRequired(f"{field['name']} must be a number, got {raw!r}") from None
        elif field["type"] == "email" and "@" not in str(raw):
            raise MissingRequired(f"{field['name']} must be an email address, got {raw!r}")
        else:
            cleaned[key] = raw
    return cleaned


def submit(conn, table, fields, values, row_id=None, id_column="id", extra=None):
    """Validates a real submission and writes a real row. Unique fields are
    checked against what is really in the table, not assumed.

    `extra` is for columns the application sets itself rather than collecting
    from the person — created_at/updated_at and the like. They are written
    alongside the form's own values and are never accepted from the form:
    anything in `values` that the record does not declare is still refused."""
    cleaned = validate(fields, values)
    for field in fields:
        if field.get("unique") == "yes":
            key = _slug(field["name"])
            if cleaned.get(key) is not None:
                clash = conn.execute(
                    f'SELECT "{id_column}" FROM "{table}" WHERE "{key}" = ?', (cleaned[key],)).fetchone()
                if clash:
                    raise NotUnique(f"{field['name']} {cleaned[key]!r} is already used by {clash[0]}")

    cleaned.update(extra or {})
    columns = list(cleaned)
    if row_id is not None:
        columns_sql = ", ".join(f'"{c}"' for c in [id_column] + columns)
        placeholders = ", ".join("?" * (len(columns) + 1))
        conn.execute(f'INSERT INTO "{table}" ({columns_sql}) VALUES ({placeholders})',
                     [row_id] + [cleaned[c] for c in columns])
    else:
        columns_sql = ", ".join(f'"{c}"' for c in columns)
        placeholders = ", ".join("?" * len(columns))
        conn.execute(f'INSERT INTO "{table}" ({columns_sql}) VALUES ({placeholders})',
                     [cleaned[c] for c in columns])
        row_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    return row_id


def prove():
    """Real proof: Command Desk's own 'Add an agent' form — rendered from
    the Agent record's real declared fields, read back out of the rendered
    HTML by an independent parser, then really submitted into a real sqlite
    table, then three real refusals."""
    fields = [
        {"name": "Name", "type": "short_text", "required": "yes", "unique": "yes"},
        {"name": "Role", "type": "short_text", "required": "yes", "unique": "no"},
        {"name": "Model", "type": "short_text", "required": "yes", "unique": "no"},
        {"name": "Instructions", "type": "long_text", "required": "yes", "unique": "no"},
        {"name": "Is on", "type": "yes_no", "required": "yes", "unique": "no"},
        {"name": "Reports to", "type": "link", "required": "yes", "unique": "no",
         "target_record": "Agent"},
    ]
    form = render_form("Agent", fields, "/agents", link_options={"Reports to": ["hub"]})

    # independent read-back: parse the rendered HTML with the stdlib parser
    # (not the same code path that wrote it) and see what controls really exist
    controls, required_in_html = read_back(form)

    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE agents (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, role TEXT, "
                 "model TEXT, instructions TEXT, is_on INTEGER, reports_to TEXT)")
    row_id = submit(conn, "agents", fields, {
        "name": "research", "role": "web research", "model": "qwen2.5",
        "instructions": "find things and cite them", "is_on": "on", "reports_to": "hub"})
    stored = conn.execute("SELECT name, role, is_on, reports_to FROM agents WHERE id = ?",
                          (row_id,)).fetchone()

    refusals = {}
    try:
        submit(conn, "agents", fields, {"name": "second", "role": "r", "model": "m",
                                        "instructions": "i", "is_on": "on", "reports_to": "hub",
                                        "salary": "100"})
    except FieldNotDeclared as err:
        refusals["a field the record does not declare"] = str(err)
    try:
        submit(conn, "agents", fields, {"name": "third", "role": "", "model": "m",
                                        "instructions": "i", "is_on": "on", "reports_to": "hub"})
    except MissingRequired as err:
        refusals["a required field left empty"] = str(err)
    try:
        submit(conn, "agents", fields, {"name": "research", "role": "r", "model": "m",
                                        "instructions": "i", "is_on": "on", "reports_to": "hub"})
    except NotUnique as err:
        refusals["a duplicate of a unique field"] = str(err)

    assert set(controls) == {"name", "role", "model", "instructions", "is_on", "reports_to"}, controls
    assert controls["is_on"] == "checkbox" and controls["name"] == "text"
    assert controls["instructions"] == "textarea" and controls["reports_to"] == "select"
    assert required_in_html == set(controls), required_in_html
    assert stored == ("research", "web research", 1, "hub"), stored
    assert conn.execute("SELECT COUNT(*) FROM agents").fetchone()[0] == 1, \
        "not one refused submission may have written a row"
    assert len(refusals) == 3, refusals
    conn.close()
    return {"engine": "form_render_submit",
            "real_system": "real rendered HTML, read back by an independent parser, + sqlite3 (:memory:)",
            "steps": ["render the real 'Add an agent' form from the Agent record's own declared fields",
                      "parse the rendered HTML back: every field has a real control of the right type",
                      "submit a real filled form -> a real row exists",
                      "refuse a value for a field the record does not declare",
                      "refuse a required field left empty",
                      "refuse a duplicate of a unique field",
                      "confirm no refused submission wrote anything"],
            "observed": {"controls": controls, "required": sorted(required_in_html),
                         "stored_row": stored, "refusals": refusals}}


if __name__ == "__main__":
    import pprint
    pprint.pprint(prove())
