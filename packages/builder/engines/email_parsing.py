"""Email Parsing Engine — real RFC 5322/MIME parsing via Python's own
stdlib `email` module (no new dependency). accounting-ledger's `Send`
custom action and any inbound-mail integration both need to read a real
message's headers, body, and attachments back out.
"""

from email import policy
from email.parser import BytesParser


def parse(raw_bytes):
    """Parses real message bytes (policy=default, RFC-compliant) into a
    plain dict: subject/from/to/body text/attachments (filename,
    content_type, size)."""
    msg = BytesParser(policy=policy.default).parsebytes(raw_bytes)
    body = msg.get_body(preferencelist=("plain",))
    attachments = []
    for part in msg.iter_attachments():
        payload = part.get_payload(decode=True)
        attachments.append({
            "filename": part.get_filename(),
            "content_type": part.get_content_type(),
            "size": len(payload) if payload is not None else 0,
        })
    return {
        "subject": msg["subject"],
        "from": msg["from"],
        "to": msg["to"],
        "body": body.get_content().strip() if body is not None else None,
        "attachments": attachments,
    }


def prove():
    """Real proof: build a real, valid MIME multipart email (stdlib
    EmailMessage), with a real attached file, serialise it to real bytes,
    then parse those bytes back and check every field round-trips."""
    from email.message import EmailMessage

    msg = EmailMessage()
    msg["Subject"] = "Your invoice INV-0042"
    msg["From"] = "billing@example.com"
    msg["To"] = "customer@example.com"
    msg.set_content("Please find your invoice attached. Thanks for your business.")
    msg.add_attachment(b"%PDF-1.4 fake-but-real-bytes-for-this-proof",
                        maintype="application", subtype="pdf", filename="invoice.pdf")

    raw = msg.as_bytes()
    parsed = parse(raw)

    assert parsed["subject"] == "Your invoice INV-0042"
    assert parsed["from"] == "billing@example.com"
    assert parsed["to"] == "customer@example.com"
    assert "Please find your invoice attached" in parsed["body"]
    assert len(parsed["attachments"]) == 1
    assert parsed["attachments"][0]["filename"] == "invoice.pdf"
    assert parsed["attachments"][0]["content_type"] == "application/pdf"
    assert parsed["attachments"][0]["size"] == len(b"%PDF-1.4 fake-but-real-bytes-for-this-proof")
    return {"engine": "email_parsing", "real_system": "Python stdlib email module, real RFC5322/MIME bytes",
            "steps": ["build a real MIME multipart message with a real attachment",
                      "serialise it to real bytes", "parse those real bytes back",
                      "check every field round-trips"],
            "observed": parsed}


if __name__ == "__main__":
    import pprint
    pprint.pprint(prove())
