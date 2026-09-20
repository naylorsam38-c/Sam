# A minimal local SMTP server for verifying apps whose signup/login flow
# requires a real outbound email (magic link, OTP code, etc.) when no real
# SMTP server is reachable in this sandbox. Point the app's SMTP_HOST at
# 127.0.0.1 and SMTP_PORT at 1025 (leave auth on unless the app requires it);
# every message it actually sends is appended, in full including its real
# HTML body, to OUT below -- read the real token/code out of that, don't
# fabricate one. Requires `pip install aiosmtpd`. Usage:
#   python3 smtp_catcher.py &
import asyncio, os
from aiosmtpd.controller import Controller

OUT = os.environ.get("SMTP_CATCHER_LOG", "/tmp/received_emails.log")

class DumpHandler:
    async def handle_DATA(self, server, session, envelope):
        with open(OUT, "a") as f:
            f.write("=== MESSAGE ===\n")
            f.write(f"From: {envelope.mail_from}\n")
            f.write(f"To: {envelope.rcpt_tos}\n")
            f.write(envelope.content.decode("utf-8", errors="replace"))
            f.write("\n\n")
        return "250 OK"

async def main():
    controller = Controller(DumpHandler(), hostname="127.0.0.1", port=1025)
    controller.start()
    print("SMTP catcher listening on 127.0.0.1:1025")
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
