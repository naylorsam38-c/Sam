"""Rendering: CPU fallback (always available) + GPU adapters + compositor."""
from .base import Renderer, FaceAnchors, NOVA
from .fallback import FallbackRenderer

__all__ = ["Renderer", "FaceAnchors", "NOVA", "FallbackRenderer"]
