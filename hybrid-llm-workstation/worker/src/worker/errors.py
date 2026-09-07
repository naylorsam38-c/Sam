class TaskExecutionError(Exception):
    """Non-retryable failure: the task is wrong or the target is
    permanently unavailable (e.g. model doesn't exist)."""


class RetryableTaskError(Exception):
    """Transient failure (network blip, GPU boot timeout, inference engine
    briefly unavailable) — eligible for automatic retry up to
    TASK_MAX_RETRIES (spec section 12)."""
