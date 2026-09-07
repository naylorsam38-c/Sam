from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from control.deps import get_db, get_settings_dep
from control.execution.agent_client import AgentClient
from workstation_core.cloud_client import CloudInferenceClient
from workstation_core.config import Settings
from workstation_core.models_orm import Worker
from workstation_core.ollama_client import OllamaClient
from workstation_core.schemas import HealthOut

router = APIRouter(prefix="/health", tags=["health"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


@router.get("", response_model=HealthOut)
async def health_root(settings: Settings = Depends(get_settings_dep)) -> HealthOut:
    return HealthOut(component="control-api", healthy=True, detail="ok", checked_at=_now())


@router.get("/local-ollama", response_model=HealthOut)
async def health_local_ollama(settings: Settings = Depends(get_settings_dep)) -> HealthOut:
    healthy, detail = await OllamaClient(settings.ollama_local_url).health()
    return HealthOut(component="local-ollama", healthy=healthy, detail=detail, checked_at=_now())


@router.get("/cloud", response_model=HealthOut)
async def health_cloud(settings: Settings = Depends(get_settings_dep)) -> HealthOut:
    client = CloudInferenceClient(settings.cloud_llm_base_url, settings.cloud_llm_api_key, settings.cloud_llm_engine)
    healthy, detail = await client.health()
    return HealthOut(component="cloud-inference", healthy=healthy, detail=detail, checked_at=_now())


@router.get("/worker", response_model=HealthOut)
async def health_worker(db: Session = Depends(get_db)) -> HealthOut:
    workers = db.query(Worker).all()
    stale_after = timedelta(seconds=90)
    active = [w for w in workers if w.last_heartbeat and _now() - w.last_heartbeat.replace(tzinfo=timezone.utc) < stale_after]
    healthy = len(active) > 0
    detail = f"{len(active)}/{len(workers)} worker(s) heartbeating" if workers else "no worker has ever registered"
    return HealthOut(component="worker", healthy=healthy, detail=detail, checked_at=_now())


@router.get("/agent", response_model=HealthOut)
async def health_agent(settings: Settings = Depends(get_settings_dep)) -> HealthOut:
    client = AgentClient(settings.execution_agent_url, settings.execution_agent_token)
    healthy, detail = await client.health()
    return HealthOut(component="local-agent", healthy=healthy, detail=detail, checked_at=_now())
