#!/usr/bin/env python3
"""
Mock Command Desk (for local Phase-3 testing only).

Stands in for your real brain: accepts POST /chat and STREAMS a response back in
small chunks (simulating token streaming), so the avatar can start speaking
before the full answer arrives. Also accepts POST /chat/interrupted.

    uvicorn scripts.mock_commanddesk:app --port 8791

This is a TEST DOUBLE. Your real Command Desk is never modified or replaced.
"""
import asyncio

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

app = FastAPI(title="Mock Command Desk")

CANNED = ("Here is what I found. ", "The report is ready, ",
          "and the numbers look healthy. ", "Would you like me to email it to you?")


@app.post("/chat")
async def chat(req: Request):
    body = await req.json()

    async def stream():
        for chunk in CANNED:
            await asyncio.sleep(0.05)      # simulate token latency
            yield chunk

    return StreamingResponse(stream(), media_type="text/plain")


@app.post("/chat/interrupted")
async def interrupted(req: Request):
    body = await req.json()
    return {"ok": True, "session_id": body.get("session_id"),
            "turn_id": body.get("turn_id")}
