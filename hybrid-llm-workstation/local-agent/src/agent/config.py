"""Local execution agent configuration.

Deliberately independent of workstation_core.config: the agent is meant to
be runnable on its own, on a machine that has nothing else from this repo
installed, with its own minimal dependency set (FastAPI/uvicorn + PyYAML +
stdlib only — no SQLAlchemy, no shared ORM).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    agent_host: str = "0.0.0.0"
    agent_port: int = 8787

    execution_agent_token: str = "change-me-to-a-different-long-random-value"
    max_request_age_seconds: int = 60

    policies_path: Path = REPO_ROOT / "config" / "policies.yaml"
    audit_db_path: Path = REPO_ROOT / "local-agent" / "data" / "audit.db"

    command_timeout_seconds: int = 300
    max_read_file_bytes: int = 1_000_000


@lru_cache
def get_agent_settings() -> AgentSettings:
    return AgentSettings()
