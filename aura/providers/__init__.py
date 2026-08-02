"""
Swappable engine providers.

Importing this package registers every built-in provider, so `registry.resolve`
can find them. Adding a new engine means adding one module here and one
`register()` call — no change to any worker, session or transport.
"""
from . import avatar, stt, tts  # noqa: F401  (import registers the providers)
from .base import (Cost, ProviderInfo, ProviderUnavailable, Requires, Tier,
                   Transcript)
from .registry import (Resolution, available, estimate_cost_per_minute,
                       register, resolve)

__all__ = ["Cost", "ProviderInfo", "ProviderUnavailable", "Requires", "Tier",
           "Transcript", "Resolution", "available", "estimate_cost_per_minute",
           "register", "resolve"]
