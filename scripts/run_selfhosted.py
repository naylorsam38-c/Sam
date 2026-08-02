#!/usr/bin/env python3
"""
Run the WHOLE thing self-hosted in one process — gateway + WebRTC + pipeline.
No LiveKit server, no paid service. Open clients/browser/webrtc.html against it.

    python scripts/run_selfhosted.py            # serves on :8080
    # then browse the gateway origin and open webrtc.html (or serve it statically)

Point AURA_BRAIN_ENDPOINT at your real Command Desk; set AURA_TOKEN_SECRET in prod.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uvicorn  # noqa: E402

if __name__ == "__main__":
    uvicorn.run("aura.gateway.app:app", host="0.0.0.0",
                port=int(os.getenv("PORT", "8080")))
