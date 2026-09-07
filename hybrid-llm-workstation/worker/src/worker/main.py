"""Worker process entrypoint.

Run with:
    python -m worker.main
or `make worker-dev` (see repo Makefile for PYTHONPATH setup). Start as many
of these as you like (spec: "multiple workers may run concurrently") — they
coordinate purely through the shared database, no direct communication.
"""

from __future__ import annotations

import asyncio
import logging

from worker.runner import WorkerRunner
from workstation_core.config import get_settings
from workstation_core.db import get_sessionmaker, init_db


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = get_settings()
    init_db(settings.database_url)
    runner = WorkerRunner(settings, get_sessionmaker())
    asyncio.run(runner.run_forever())


if __name__ == "__main__":
    main()
