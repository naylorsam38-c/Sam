"""Central configuration, loaded from environment variables (spec section 4).

Every setting has an explicit, safe default so the system is usable with the
cloud GPU off and without cloud credentials configured (spec principle #12).
Nothing here silently fabricates a credential or endpoint: if a cloud/GPU
value is unset, the relevant client reports "unavailable" rather than
guessing a URL.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    database_url: str = f"sqlite:///{REPO_ROOT / 'data' / 'workstation.db'}"

    auth_secret: str = "change-me-dev-only-not-for-production"
    auth_token_ttl_minutes: int = 60 * 24

    ollama_local_url: str = "http://localhost:11434"

    cloud_llm_base_url: str = ""
    cloud_llm_api_key: str = ""
    cloud_llm_engine: str = "ollama"  # "ollama" or "vllm"

    gpu_provider: str = "mock"  # mock | runpod | vast | lambdalabs
    gpu_provider_api_key: str = ""
    gpu_template_id: str = ""
    gpu_volume_id: str = ""

    gpu_idle_timeout_minutes: int = 20
    gpu_max_session_minutes: int = 240
    gpu_max_hourly_cost: float = 2.00
    gpu_auto_stop: bool = True
    gpu_auto_start: bool = True
    gpu_estimated_hourly_cost: float = 0.50  # used when a provider can't report live cost

    # Not one of spec section 4's literal env vars, but required by the
    # architecture: the worker process talks to the control API over HTTP
    # only for GPU start/stop (the control API is the sole owner of the
    # live provider connection — see apps/control/src/control/gpu/lifecycle.py).
    control_api_url: str = "http://localhost:8000"

    task_max_retries: int = 3
    task_timeout_seconds: int = 900
    worker_poll_interval_seconds: float = 2.0
    gpu_monitor_interval_seconds: float = 30.0

    execution_agent_url: str = "http://localhost:8787"
    execution_agent_public_key: str = ""
    execution_agent_token: str = "change-me-dev-only-not-for-production"

    notification_enabled: bool = True

    config_dir: Path = REPO_ROOT / "config"

    @property
    def models_config_path(self) -> Path:
        return self.config_dir / "models.yaml"

    @property
    def providers_config_path(self) -> Path:
        return self.config_dir / "providers.yaml"

    @property
    def policies_config_path(self) -> Path:
        return self.config_dir / "policies.yaml"

    @property
    def notifications_config_path(self) -> Path:
        return self.config_dir / "notifications.yaml"


@lru_cache
def get_settings() -> Settings:
    return Settings()
