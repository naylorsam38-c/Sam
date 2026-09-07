"""Stable Ollama-protocol reverse proxy to whatever the cloud GPU's actual
endpoint currently is (spec section 5: Open WebUI shouldn't need to know
infrastructure details, and the cloud endpoint changes IP/port every
session). Point Open WebUI's "Ollama API" connection at
http://<control-host>:<port>/proxy/cloud with OPEN_WEBUI_PROXY_TOKEN as its
API key, and it keeps working across GPU restarts without reconfiguration.
"""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from control.deps import get_db, get_gpu_manager, get_settings_dep
from control.gpu.lifecycle import GPULifecycleManager
from workstation_core.config import Settings
from workstation_core.enums import GPUStatus
from workstation_core.gpu_activity import mark_gpu_activity

router = APIRouter(prefix="/proxy/cloud", tags=["proxy"])

_FORWARDED_REQUEST_HEADERS = {"content-type", "accept"}


def _check_proxy_token(request: Request, settings: Settings) -> None:
    if not settings.open_webui_proxy_token:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "OPEN_WEBUI_PROXY_TOKEN is not configured")
    provided = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
    if provided != settings.open_webui_proxy_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid proxy token")


@router.api_route("/{path:path}", methods=["GET", "POST"])
async def proxy_to_cloud_gpu(
    path: str, request: Request, db: Session = Depends(get_db),
    manager: GPULifecycleManager = Depends(get_gpu_manager), settings: Settings = Depends(get_settings_dep),
) -> Response:
    _check_proxy_token(request, settings)

    session = await manager.get_status(db)
    endpoint = (session.session_metadata or {}).get("endpoint")
    if session.status not in (GPUStatus.READY.value, GPUStatus.BUSY.value, GPUStatus.IDLE.value) or not endpoint:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            f"cloud GPU is not ready (status={session.status}); start it via POST /api/gpu/start",
        )

    is_inference_call = path.rstrip("/") in ("api/chat", "api/generate")
    if is_inference_call:
        mark_gpu_activity(db, busy=True)
        db.commit()

    try:
        body = await request.body()
        forward_headers = {k: v for k, v in request.headers.items() if k.lower() in _FORWARDED_REQUEST_HEADERS}
        async with httpx.AsyncClient(timeout=180.0) as client:
            upstream = await client.request(
                request.method, f"{endpoint.rstrip('/')}/{path}", content=body, headers=forward_headers,
                params=dict(request.query_params),
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"cloud endpoint unreachable: {exc}") from exc
    finally:
        if is_inference_call:
            mark_gpu_activity(db, busy=False)
            db.commit()

    return Response(
        content=upstream.content, status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type"),
    )
