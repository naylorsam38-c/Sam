#!/usr/bin/env python3
"""Launch the Aura runtime for one user (spec §25)."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aura.runtime import run_forever  # noqa: E402

if __name__ == "__main__":
    asyncio.run(run_forever(os.getenv("AURA_SESSION_ID", "primary")))
