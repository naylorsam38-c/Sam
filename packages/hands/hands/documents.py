"""Document storage — the original is preserved, the completed copy is a
separate file.

Two rules are enforced here rather than trusted:

  * the original's bytes are hashed on intake and re-hashed at completion,
    so "the original was preserved" is a checked fact, not a claim;
  * the completed copy is written to its own path, and writing it refuses
    if that path is the original's.
"""

import hashlib
import time
import uuid
from pathlib import Path

from . import config, session as sess, shelf, store


class DocumentError(RuntimeError):
    pass


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _session_dir(session_id, root=None):
    return store.data_root(root) / "sessions" / session_id


def safe_filename(filename):
    """A filename is customer input, so it never becomes part of a path
    until it has been checked. Anything with a directory component in it —
    `../`, an absolute path, a Windows separator — is refused outright
    rather than quietly rewritten, because a rewritten name no longer
    matches the document the customer thinks they uploaded."""
    if not filename or filename in (".", ".."):
        raise DocumentError("a document needs a filename")
    if "/" in filename or "\\" in filename or Path(filename).name != filename:
        raise DocumentError(f"{filename!r} is a path, not a filename")
    return filename


def store_original(conn, session_id, filename, data, root=None):
    """Writes the customer's uploaded document once. A second upload under
    the same filename is refused — originals are never overwritten."""
    filename = safe_filename(filename)
    if len(data) > config.MAX_UPLOAD_BYTES:
        raise DocumentError(
            f"{filename} is {len(data)} bytes; the limit is {config.MAX_UPLOAD_BYTES} "
            f"(MAX_UPLOAD_BYTES in config.py)")
    if not data:
        raise DocumentError(f"{filename} is empty")
    directory = _session_dir(session_id, root) / "originals"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / filename
    if path.exists():
        raise DocumentError(f"{filename} already stored for {session_id} — originals are write-once")
    path.write_bytes(data)

    document_id = f"DOC-{uuid.uuid4().hex[:12]}"
    conn.execute(
        "INSERT INTO documents (id, session_id, role, filename, path, sha256, byte_length, created_at) "
        "VALUES (?, ?, 'original', ?, ?, ?, ?, ?)",
        (document_id, session_id, filename, str(path), _sha256(data), len(data), time.time()))
    conn.commit()
    sess.log(conn, session_id, "original_stored",
             {"filename": filename, "sha256": _sha256(data), "bytes": len(data)})
    return document_id


def get_document(conn, document_id):
    row = conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
    if row is None:
        raise DocumentError(f"no such document {document_id!r}")
    return dict(row)


def documents_for(conn, session_id, role=None):
    if role:
        rows = conn.execute("SELECT * FROM documents WHERE session_id = ? AND role = ? ORDER BY created_at",
                            (session_id, role)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM documents WHERE session_id = ? ORDER BY created_at",
                            (session_id,)).fetchall()
    return [dict(r) for r in rows]


def original_intact(conn, session_id):
    """Re-reads every original from disk and compares against the hash
    recorded at intake. False means something wrote to the customer's own
    file, which must never happen."""
    for doc in documents_for(conn, session_id, role="original"):
        data = Path(doc["path"]).read_bytes()
        if _sha256(data) != doc["sha256"]:
            return False
    return True


def write_completed(conn, session_id, original_document_id, fields, title, root=None):
    """Renders the completed copy from the real detected fields, as a NEW
    file beside the original, and attests its real bytes."""
    original = get_document(conn, original_document_id)
    directory = _session_dir(session_id, root) / "completed"
    directory.mkdir(parents=True, exist_ok=True)
    stem = Path(original["filename"]).stem
    path = directory / f"{stem}-completed.pdf"
    if str(path) == original["path"]:
        raise DocumentError("the completed copy may not be written over the original")

    render_fields = [{"name": f["name"], "label": f["label"], "value": f["value"], "rect": f["rect"]}
                     for f in fields]
    shelf.pdf_form_filling.render_pdf_with_form(str(path), title, render_fields)

    data = path.read_bytes()
    document_id = f"DOC-{uuid.uuid4().hex[:12]}"
    conn.execute(
        "INSERT INTO documents (id, session_id, role, filename, path, sha256, byte_length, created_at) "
        "VALUES (?, ?, 'completed', ?, ?, ?, ?, ?)",
        (document_id, session_id, path.name, str(path), _sha256(data), len(data), time.time()))
    conn.commit()
    sess.log(conn, session_id, "completed_copy_written",
             {"filename": path.name, "sha256": _sha256(data), "bytes": len(data)})
    return document_id


def attest(conn, document_id):
    """Attests the completed copy's real bytes. Separate from writing it,
    because attesting is its own gated action: the customer approves the
    document they reviewed, and the attestation covers exactly those
    bytes."""
    doc = get_document(conn, document_id)
    if doc["role"] != "completed":
        raise DocumentError("only a completed copy is attested; the original is never touched")
    data = Path(doc["path"]).read_bytes()
    if _sha256(data) != doc["sha256"]:
        raise DocumentError("the completed copy changed since it was written — refusing to attest it")
    attestation = shelf.document_signing.sign(config.signing_secret(), data)
    conn.execute("UPDATE documents SET attestation = ? WHERE id = ?", (attestation, document_id))
    conn.commit()
    sess.log(conn, doc["session_id"], "completed_copy_attested",
             {"document_id": document_id, "sha256": doc["sha256"]})
    return attestation


def attestation_valid(conn, document_id):
    """Checks the completed copy's recorded attestation against the bytes
    that are on disk right now."""
    doc = get_document(conn, document_id)
    if not doc["attestation"]:
        return False
    data = Path(doc["path"]).read_bytes()
    return shelf.document_signing.verify(config.signing_secret(), data, doc["attestation"])
