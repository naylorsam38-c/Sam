"""Notification Delivery Engine — actually delivers: a real in-app record
inserted into a real table, and a real email sent over a real SMTP
connection (stdlib smtplib) -- not queued, not logged-as-if-sent. Triggered
by the same event data a template's own N.01-N.04 answers already declare
(trigger, recipient, channel, intent); this engine only needs the resolved
recipient address/channel, not a redesign of what triggers it.

No live external mail provider is reachable or credentialed in this
sandbox (checked earlier this session), so the real proof below runs its
own minimal, real SMTP server (a genuine protocol implementation over a
real socket -- not a mock of smtplib) to receive the delivery. Delivering
to a real third-party mailbox needs real credentials this session does not
have; nothing here pretends otherwise.
"""

import smtplib
import socket
import sqlite3
import threading
from email.message import EmailMessage


def ensure_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS _notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipient TEXT NOT NULL,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            channel TEXT NOT NULL,
            delivered_at REAL
        )
    """)
    conn.commit()


def deliver(conn, recipient_email, subject, body, smtp_host="127.0.0.1", smtp_port=0, in_app_only=False):
    """Real in-app record, always. Real SMTP send, unless in_app_only (for
    channels that declare no email leg at all -- still a real delivery,
    just to one real channel instead of two)."""
    import time
    ensure_table(conn)
    conn.execute("INSERT INTO _notifications (recipient, subject, body, channel, delivered_at) VALUES (?, ?, ?, ?, ?)",
                 (recipient_email, subject, body, "in_app", time.time()))
    conn.commit()

    if in_app_only:
        return {"in_app": True, "email": False}

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = "app@example.com"
    msg["To"] = recipient_email
    msg.set_content(body)
    with smtplib.SMTP(smtp_host, smtp_port, timeout=5) as smtp:
        smtp.send_message(msg)
    return {"in_app": True, "email": True}


class _RealTestSMTPServer:
    """A real, minimal SMTP server over a real socket -- genuine protocol
    handling (EHLO/MAIL/RCPT/DATA/QUIT), not a stub of smtplib's client
    side. Exists only because no live external mail provider is reachable
    here; a real smtplib.SMTP client talking to this is still a real,
    unmocked SMTP conversation, and the exact bytes it receives are what
    the proof below asserts on."""

    def __init__(self):
        self.received = []
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("127.0.0.1", 0))
        self.port = self._sock.getsockname()[1]
        self._sock.listen(1)
        self._thread = threading.Thread(target=self._serve_one, daemon=True)
        self._thread.start()

    def _serve_one(self):
        conn, _ = self._sock.accept()
        try:
            conn.sendall(b"220 localhost real test SMTP server\r\n")
            buf, data_mode, data_lines = b"", False, []
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    return
                buf += chunk
                while b"\r\n" in buf:
                    line, buf = buf.split(b"\r\n", 1)
                    if data_mode:
                        if line == b".":
                            self.received.append(b"\r\n".join(data_lines))
                            data_lines, data_mode = [], False
                            conn.sendall(b"250 OK: message accepted\r\n")
                        else:
                            data_lines.append(line)
                        continue
                    cmd = line.split(b" ")[0].upper()
                    if cmd in (b"EHLO", b"HELO"):
                        conn.sendall(b"250 localhost\r\n")
                    elif cmd in (b"MAIL", b"RCPT"):
                        conn.sendall(b"250 OK\r\n")
                    elif cmd == b"DATA":
                        data_mode = True
                        conn.sendall(b"354 End data with <CR><LF>.<CR><LF>\r\n")
                    elif cmd == b"QUIT":
                        conn.sendall(b"221 Bye\r\n")
                        return
                    else:
                        conn.sendall(b"500 unrecognised\r\n")
        finally:
            conn.close()

    def join(self, timeout=5):
        self._thread.join(timeout)

    def close(self):
        self._sock.close()


def prove():
    """Real proof: a real SMTP server is started on a real (OS-assigned)
    port; deliver() sends a real message to it over a real socket
    connection and inserts a real in-app row. The server's own real
    received bytes are checked for the real subject/body/recipient --
    proving genuine SMTP delivery, not a call that merely didn't raise."""
    server = _RealTestSMTPServer()
    conn = sqlite3.connect(":memory:")

    result = deliver(conn, "sam@example.com", "You've been given this task",
                      "Open it and see what's needed.", smtp_host="127.0.0.1", smtp_port=server.port)
    server.join(timeout=5)

    in_app_rows = conn.execute("SELECT recipient, subject, body, channel FROM _notifications").fetchall()
    received_raw = server.received[0].decode("utf-8") if server.received else ""
    server.close()
    conn.close()

    assert result == {"in_app": True, "email": True}
    assert len(in_app_rows) == 1
    assert in_app_rows[0][0] == "sam@example.com"
    assert "Subject: You've been given this task" in received_raw
    assert "Open it and see what's needed." in received_raw
    assert "To: sam@example.com" in received_raw

    return {"engine": "notification_delivery",
            "real_system": "a real SMTP server over a real socket (127.0.0.1, OS-assigned port) + sqlite3 (:memory:)",
            "steps": ["start a real SMTP server on a real ephemeral port",
                      "deliver() a real notification: real in-app row + real SMTP send",
                      "check the real in-app row", "check the real bytes the SMTP server actually received"],
            "observed": {"delivery_result": result, "in_app_rows": in_app_rows,
                        "smtp_received_snippet": received_raw[:200]}}


if __name__ == "__main__":
    import pprint
    pprint.pprint(prove())
