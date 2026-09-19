#!/usr/bin/env python3
"""
shelf_records.py — Registry stage.

Scans SHELF_ROOT for harvested capabilities (every shelf/<app-slug>/<CAP-ID>/
directory with a PROVENANCE.json in it) and writes one aggregated registry
record per capability to REGISTRY_ROOT/<CAP-ID>.json. build.py reads from
the registry, never from the shelf directly -- the registry is the stable
public interface; the shelf layout is an implementation detail underneath it.

Run: python3 shelf_records.py
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

# ----------------------------------------------------------------------------
# CONFIG — human-friendly aliases per capability, used for later lookup by
# the build/adapter system (e.g. so "csv export", "download export" also
# resolve to CAP-0001). Purely descriptive; does not affect what was
# harvested or its provenance.
# ----------------------------------------------------------------------------
CAPABILITY_ALIASES = {
    "CAP-0001": ["export", "csv export", "download export", "export data"],
}
# ----------------------------------------------------------------------------


def main():
    config.ensure_dirs()
    config.print_roots(__file__)

    by_cap = {}
    for provenance_path in sorted(config.SHELF_ROOT.glob("*/*/PROVENANCE.json")):
        provenance = config.load_json(provenance_path)
        cap_id = provenance["cap_id"]
        shelf_dir = provenance_path.parent
        impl = {
            "app_slug": provenance["application"]["slug"],
            "shelf_path": str(shelf_dir.relative_to(config.PROJECT_ROOT)),
            "provenance_path": str(provenance_path.relative_to(config.PROJECT_ROOT)),
            "licence": provenance["licence"]["id"],
            "commit": provenance["application"]["commit"],
            "harvested_at": provenance["harvested_at"],
        }
        by_cap.setdefault(cap_id, {
            "cap_id": cap_id,
            "name": provenance["capability_name"],
            "category": provenance["category"],
            "aliases": CAPABILITY_ALIASES.get(cap_id, []),
            "implementations": [],
        })["implementations"].append(impl)

    written = []
    for cap_id, record in sorted(by_cap.items()):
        record["generated_at"] = datetime.now(timezone.utc).isoformat()
        out_path = config.REGISTRY_ROOT / f"{cap_id}.json"
        config.write_json(out_path, record)
        written.append(out_path)
        print(f"  [{cap_id}] {record['name']}: {len(record['implementations'])} implementation(s) -> {out_path}")

    if not written:
        print("  (no shelf records found -- nothing to register)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
