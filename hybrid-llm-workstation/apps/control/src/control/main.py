"""Control API entrypoint (spec section 2.4). Run with:

    uvicorn control.main:app --host 0.0.0.0 --port 8000

or `make control-dev` (sets PYTHONPATH correctly — see repo Makefile).
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from workstation_core.config import get_settings
from workstation_core.db import get_sessionmaker, init_db

from control.api import approvals, auth, execution, gpu, health, models, notifications, tasks
from control.gpu.lifecycle import GPULifecycleManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    init_db(settings.database_url)
    app.state.settings = settings
    app.state.gpu_manager = GPULifecycleManager(settings, get_sessionmaker())
    await app.state.gpu_manager.reconcile_on_startup()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Personal LLM Workstation — Control API",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(health.router)
    app.include_router(models.router)
    app.include_router(gpu.router)
    app.include_router(tasks.router)
    app.include_router(notifications.router)
    app.include_router(approvals.router)
    app.include_router(execution.router)

    return app


app = create_app()
