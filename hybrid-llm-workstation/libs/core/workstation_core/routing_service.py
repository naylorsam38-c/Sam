"""Model/environment routing (spec section 10).

Three modes, matching the spec exactly:

  explicit   — the request names a model_id (and/or environment). We only
               ever use that model; if it isn't available we fail loudly
               rather than silently substituting another one.
  automatic  — the request sets input.routing_mode == "automatic" plus
               input.required_capabilities. The router then picks the best
               available match under cost policy.
  background — a queued task with no model_id set is resolved the same way
               as "automatic" at claim time, using whatever the task's
               input specifies as requirements.

Per spec: "Default behaviour must favour explicit user choice until
automatic routing is deliberately enabled." We implement that literally —
automatic selection only ever happens when routing_mode is explicitly set
to "automatic" in the request; otherwise an unspecified model/environment
is a client error, not a silent guess.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session
from workstation_core.enums import Environment, ModelStatus
from workstation_core.models_orm import ModelRecord


class RoutingError(Exception):
    pass


def resolve(
    db: Session, *, model_id: str | None, environment: str | None, input_: dict[str, Any] | None = None,
) -> ModelRecord:
    input_ = input_ or {}

    if model_id:
        model = db.get(ModelRecord, model_id)
        if model is None:
            raise RoutingError(f"model '{model_id}' does not exist in the registry")
        if model.status != ModelStatus.AVAILABLE.value:
            raise RoutingError(
                f"model '{model.name}' ({model.environment}) is not currently available "
                "(refresh the registry or check GPU status)"
            )
        if environment and model.environment != environment:
            raise RoutingError(
                f"model '{model.name}' is in environment '{model.environment}', not requested '{environment}'"
            )
        return model

    if input_.get("routing_mode") == "automatic":
        return _automatic(db, environment=environment, required_capabilities=input_.get("required_capabilities", []))

    if environment:
        candidates = (
            db.query(ModelRecord)
            .filter(ModelRecord.environment == environment, ModelRecord.status == ModelStatus.AVAILABLE.value)
            .order_by(ModelRecord.updated_at.desc())
            .all()
        )
        if not candidates:
            raise RoutingError(f"no available models in environment '{environment}'")
        if len(candidates) > 1:
            raise RoutingError(
                f"multiple available models in '{environment}' and no model_id given: "
                f"{[m.name for m in candidates]}. Specify model_id explicitly."
            )
        return candidates[0]

    raise RoutingError(
        "no model_id or environment specified, and routing_mode is not 'automatic'. "
        "Explicit choice is required by default (spec section 10)."
    )


def _automatic(db: Session, *, environment: str | None, required_capabilities: list[str]) -> ModelRecord:
    query = db.query(ModelRecord).filter(ModelRecord.status == ModelStatus.AVAILABLE.value)
    if environment:
        query = query.filter(ModelRecord.environment == environment)

    candidates = query.all()
    if required_capabilities:
        candidates = [m for m in candidates if set(required_capabilities).issubset(set(m.capabilities or []))]

    if not candidates:
        raise RoutingError(
            f"automatic routing found no available model matching capabilities={required_capabilities} "
            f"environment={environment or 'any'}"
        )

    # Cost policy default: prefer local (free) over cloud; among ties,
    # prefer the most recently verified-available model.
    def sort_key(m: ModelRecord):
        cost_rank = {"free": 0, "low": 1, "medium": 2, "high": 3}.get(m.cost_class, 2)
        env_rank = 0 if m.environment == Environment.LOCAL.value else 1
        return (env_rank, cost_rank, -m.updated_at.timestamp())

    candidates.sort(key=sort_key)
    return candidates[0]
