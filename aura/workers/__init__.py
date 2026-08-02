"""Independently-managed workers (spec §7). Each obeys the BaseWorker contract
(bounded queues, health, timeout, cancellation, backpressure, logs, restart,
metrics) and can be moved to its own process/GPU later (spec §9)."""
from .audio_input import AudioInputWorker
from .vad import VADWorker
from .stt import STTWorker
from .brain import BrainConnector
from .tts import TTSWorker
from .renderer import RendererWorker
from .publisher import PublisherWorker

__all__ = ["AudioInputWorker", "VADWorker", "STTWorker", "BrainConnector",
           "TTSWorker", "RendererWorker", "PublisherWorker"]
