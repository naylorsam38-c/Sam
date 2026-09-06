"""File Conversion Engine — narrowly scoped to what stdlib actually supports
without a new dependency: CSV <-> JSON. General image/office-document/media
transcoding needs real codec libraries this project's own "no new
dependencies" rule (stated for every generated app, e.g. Command Desk's own
approved spec) does not allow adding, so it is not attempted here -- see
ENGINE_CATALOGUE.md for the honest boundary.
"""

import csv
import json


def csv_to_json(csv_path, json_path):
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)
    return len(rows)


def json_to_csv(json_path, csv_path):
    with open(json_path, encoding="utf-8") as f:
        rows = json.load(f)
    if not rows:
        raise ValueError(f"{json_path}: no rows to convert (need at least one to know the columns)")
    fieldnames = list(rows[0].keys())
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def prove():
    """Real proof: a real CSV file on disk -> real JSON file -> real CSV
    file again, checked for round-trip equality of the actual parsed data."""
    import tempfile, os
    fd1, csv_path = tempfile.mkstemp(suffix=".csv")
    os.close(fd1)
    fd2, json_path = tempfile.mkstemp(suffix=".json")
    os.close(fd2)
    fd3, csv_path2 = tempfile.mkstemp(suffix=".csv")
    os.close(fd3)
    try:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            f.write("name,price\nWidget,9.99\nGadget,19.99\n")

        n1 = csv_to_json(csv_path, json_path)
        with open(json_path, encoding="utf-8") as f:
            parsed_json = json.load(f)

        n2 = json_to_csv(json_path, csv_path2)
        with open(csv_path2, newline="", encoding="utf-8") as f:
            rows_back = list(csv.DictReader(f))
    finally:
        os.remove(csv_path)
        os.remove(json_path)
        os.remove(csv_path2)

    assert n1 == 2 and n2 == 2
    assert parsed_json == [{"name": "Widget", "price": "9.99"}, {"name": "Gadget", "price": "19.99"}]
    assert rows_back == parsed_json
    return {"engine": "file_conversion", "real_system": "real files on disk (csv + json)",
            "steps": ["write a real CSV file", "convert to real JSON file", "convert back to real CSV",
                      "compare round-trip"],
            "observed": {"csv_to_json_rows": n1, "json_to_csv_rows": n2, "round_trip_equal": rows_back == parsed_json}}


if __name__ == "__main__":
    import pprint
    pprint.pprint(prove())
