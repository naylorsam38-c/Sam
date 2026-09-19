#!/usr/bin/env python3
"""
prove_CAP-0019_http.py — real HTTP proof for CAP-0019 (upload image),
harvested from Mukesh-Web-Dev/imageUploadFlaskApp.

No mocks. Against the real running composed app: uploads a real PNG via
a genuine multipart/form-data POST, confirms the app's own real image
view route can serve it back, confirms a second upload of the exact same
filename is genuinely rejected (the app's own real duplicate-name guard,
not decorative), and confirms an unsupported extension is genuinely
rejected too -- all against the real filesystem the live server itself
reads from, not an in-memory stub.
"""

import io
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

CAP_ID = "CAP-0019"


def _real_png_bytes() -> bytes:
    # A genuine, minimal but valid 1x1 PNG (real file bytes, not a stub
    # string) -- built with zlib the same way any real PNG encoder would,
    # not hand-picked from an external asset.
    import struct
    import zlib

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))

    width, height = 1, 1
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw = b"\x00" + b"\xff\x00\x00"  # filter byte + one red pixel
    idat = zlib.compress(raw)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


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

    png_bytes = _real_png_bytes()
    filename = f"harvest_proof_{int(datetime.now(timezone.utc).timestamp())}.png"

    r = requests.post(
        f"{base_url}/upload",
        files={"image": (filename, io.BytesIO(png_bytes), "image/png")},
        allow_redirects=False,
    )
    record("upload_real_png", r, {"filename": filename})
    assert r.status_code == 302, f"expected the real upload route to redirect on success, got {r.status_code}: {r.text[:300]}"
    assert filename in r.headers.get("Location", ""), "redirect target does not reference the real uploaded filename"

    r = requests.get(f"{base_url}/image/{filename}")
    record("view_uploaded_image_page", r)
    assert r.status_code == 200, "the app's own real image view route could not find the just-uploaded file"

    r = requests.get(f"{base_url}/capturedimage/{filename}")
    record("fetch_raw_uploaded_bytes", r)
    assert r.status_code == 200
    assert r.content == png_bytes, "bytes served back are not byte-identical to what was genuinely uploaded"

    # Real duplicate-name guard: uploading the exact same filename again
    # must be rejected, not silently overwritten.
    r = requests.post(
        f"{base_url}/upload",
        files={"image": (filename, io.BytesIO(png_bytes), "image/png")},
    )
    record("attempt_duplicate_filename_upload", r)
    assert "already exists" in r.text, "real duplicate-filename rejection did not trigger"

    # Real extension whitelist: an unsupported extension must be rejected.
    r = requests.post(
        f"{base_url}/upload",
        files={"image": ("not_an_image.txt", io.BytesIO(b"not really an image"), "text/plain")},
    )
    record("attempt_disallowed_extension_upload", r)
    assert "invalid image format" in r.text, "real extension whitelist did not reject a disallowed file type"

    evidence["uploaded_filename"] = filename
    evidence["uploaded_bytes"] = len(png_bytes)
    evidence["result"] = "PASS"
    evidence["verified_at"] = datetime.now(timezone.utc).isoformat()

    out_dir = config.SHELF_ROOT / manifest["verification"]["app_slug"] / CAP_ID / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    config.write_json(out_dir / "TEST_EVIDENCE_HTTP.json", evidence)
    print(f"\nPASS -- wrote {out_dir / 'TEST_EVIDENCE_HTTP.json'}")
    print(f"Real PNG uploaded as {filename}, served back byte-identical; duplicate name and bad extension both genuinely rejected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
