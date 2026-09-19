#!/usr/bin/env python3
"""
prove_CAP-0029_http.py — real HTTP proof for CAP-0029 (capture photo),
harvested from Mukesh-Web-Dev/imageUploadFlaskApp.

No mocks. Against the real running composed app: submits a real base64
data-URL-encoded PNG (the same shape a browser's webcam <canvas> capture
would send) to the real /capture route, confirms it genuinely decodes
and saves a real PNG file to disk (distinct code path from the
multipart /upload route already harvested as CAP-0019 -- this one
exercises the real base64-decode + PIL Image.save() branch), and
confirms the real saved bytes decode back to an image with the exact
dimensions/colour submitted.
"""

import base64
import io
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

CAP_ID = "CAP-0029"


def _real_png_data_url() -> tuple[bytes, str]:
    import struct
    import zlib

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))

    width, height = 2, 2
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw = b"".join(b"\x00" + b"\x00\xff\x00" * width for _ in range(height))  # green pixels
    idat = zlib.compress(raw)
    png_bytes = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")
    data_url = "data:image/png;base64," + base64.b64encode(png_bytes).decode("ascii")
    return png_bytes, data_url


def main():
    config.print_roots(__file__)
    manifest = config.load_json(config.OUTPUT_ROOT / "build_manifest.json")
    if not manifest["verification"]["verified"]:
        raise SystemExit("ABORT: build manifest says the composed app was not verified -- refusing to test it")
    base_url = f"http://{manifest['host']}:{manifest['port']}"

    evidence = {"cap_id": CAP_ID, "base_url": base_url, "steps": []}

    def record(step, response, extra=None):
        entry = {"step": step, "method": response.request.method, "url": response.request.url, "status_code": response.status_code}
        if extra:
            entry.update(extra)
        evidence["steps"].append(entry)
        print(f"  [{step}] {response.request.method} {response.request.url} -> {response.status_code}")

    png_bytes, data_url = _real_png_data_url()

    r = requests.post(f"{base_url}/capture", data={"image": data_url})
    record("capture_real_base64_image", r)
    assert r.status_code == 200, r.text

    m = re.search(r'src="[^"]*?(img_\d{4}_\d{2}_\d{2}_\d{2}_\d{2}_\d{2}\.png)"', r.text)
    assert m, f"could not find the real generated capture filename in the response: {r.text[:500]}"
    filename = m.group(1)

    r = requests.get(f"{base_url}/capturedimage/{filename}")
    record("fetch_captured_image_bytes", r, {"filename": filename})
    assert r.status_code == 200, r.text
    assert r.content.startswith(b"\x89PNG\r\n\x1a\n"), "captured file is not a genuine PNG"

    from PIL import Image
    saved_img = Image.open(io.BytesIO(r.content))
    original_img = Image.open(io.BytesIO(png_bytes))
    assert saved_img.size == original_img.size, "saved capture does not match the real submitted image dimensions"
    assert saved_img.convert("RGB").tobytes() == original_img.convert("RGB").tobytes(), (
        "saved capture's real pixel data does not match what was genuinely submitted"
    )

    evidence["captured_filename"] = filename
    evidence["result"] = "PASS"
    evidence["verified_at"] = datetime.now(timezone.utc).isoformat()

    out_dir = config.SHELF_ROOT / manifest["verification"]["app_slug"] / CAP_ID / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    config.write_json(out_dir / "TEST_EVIDENCE_HTTP.json", evidence)
    print(f"\nPASS -- wrote {out_dir / 'TEST_EVIDENCE_HTTP.json'}")
    print(f"Real base64-captured image saved as {filename}, pixel-identical to what was submitted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
