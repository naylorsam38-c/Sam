"""Unified model registry (spec section 9).

`refresh()` is the single place that decides whether a model is
`available`: it actually calls the local Ollama API and (if the GPU is
READY) the cloud inference API, and only marks a model available if that
call succeeded. Nothing here invents a model that wasn't reported by an
inference engine (operational rule #1: "never claim a model is available
until its endpoint has been verified").
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.orm import Session
from workstation_core.cloud_client import CloudInferenceClient, CloudInferenceUnavailableError
from workstation_core.config import Settings
from workstation_core.enums import Environment, ModelStatus
from workstation_core.models_orm import ModelRecord
from workstation_core.ollama_client import OllamaClient, OllamaUnavailableError


class _MetadataCatalogue:
    def __init__(self, path: Path):
        self._data = yaml.safe_load(path.read_text()) if path.exists() else {}
        self._data = self._data or {}

    def for_model(self, name: str, environment: str) -> dict[str, Any]:
        defaults = (self._data.get("defaults") or {}).get(environment, {})
        result = {
            "capabilities": defaults.get("capabilities", []),
            "context_length": defaults.get("context_length"),
            "cost_class": defaults.get("cost_class", "free" if environment == "local" else "medium"),
        }
        base_name = name.split(":")[0]
        for override in self._data.get("overrides", []):
            match = override.get("match", "")
            if name == match or base_name == match:
                result.update({k: v for k, v in override.items() if k != "match"})
        return result


async def refresh_registry(db: Session, settings: Settings) -> dict[str, Any]:
    catalogue = _MetadataCatalogue(settings.models_config_path)
    report = {"local": {"checked": True, "healthy": False, "models": 0, "detail": ""},
              "cloud": {"checked": True, "healthy": False, "models": 0, "detail": ""}}

    seen_names: set[tuple[str, str]] = set()

    # --- Local ---
    ollama = OllamaClient(settings.ollama_local_url)
    try:
        local_models = await ollama.list_models()
        report["local"]["healthy"] = True
        report["local"]["models"] = len(local_models)
        for m in local_models:
            meta = catalogue.for_model(m.name, "local")
            _upsert(db, name=m.name, environment=Environment.LOCAL, provider="ollama", engine="ollama",
                    status=ModelStatus.AVAILABLE, meta=meta, raw=m.raw or {})
            seen_names.add((m.name, Environment.LOCAL.value))
    except OllamaUnavailableError as exc:
        report["local"]["detail"] = str(exc)

    # --- Cloud (only meaningful once the GPU is up; if not configured/ready
    #     we mark existing cloud models unavailable rather than fabricating
    #     a health state) ---
    cloud = CloudInferenceClient(settings.cloud_llm_base_url, settings.cloud_llm_api_key, settings.cloud_llm_engine)
    if cloud.configured:
        try:
            cloud_models = await cloud.list_models()
            report["cloud"]["healthy"] = True
            report["cloud"]["models"] = len(cloud_models)
            for m in cloud_models:
                meta = catalogue.for_model(m.name, "cloud")
                _upsert(db, name=m.name, environment=Environment.CLOUD, provider=settings.gpu_provider,
                        engine=settings.cloud_llm_engine, status=ModelStatus.AVAILABLE, meta=meta, raw=m.raw or {})
                seen_names.add((m.name, Environment.CLOUD.value))
        except CloudInferenceUnavailableError as exc:
            report["cloud"]["detail"] = str(exc)
    else:
        report["cloud"]["detail"] = "CLOUD_LLM_BASE_URL not configured (GPU likely OFF)"

    # Anything previously recorded but not seen this refresh is unavailable
    # now — never leave a stale "available" model in the catalogue.
    for existing in db.query(ModelRecord).all():
        key = (existing.name, existing.environment)
        if key not in seen_names and existing.status == ModelStatus.AVAILABLE.value:
            existing.status = ModelStatus.UNAVAILABLE.value

    db.flush()
    return report


def _upsert(
    db: Session, *, name: str, environment: Environment, provider: str, engine: str,
    status: ModelStatus, meta: dict[str, Any], raw: dict[str, Any],
) -> ModelRecord:
    record = (
        db.query(ModelRecord)
        .filter(ModelRecord.name == name, ModelRecord.environment == environment.value)
        .one_or_none()
    )
    if record is None:
        record = ModelRecord(name=name, environment=environment.value)
        db.add(record)

    record.provider = provider
    record.engine = engine
    record.status = status.value
    record.capabilities = meta.get("capabilities", [])
    record.context_length = meta.get("context_length")
    record.cost_class = meta.get("cost_class", "free")
    record.model_metadata = {"raw": raw}
    db.flush()
    return record
