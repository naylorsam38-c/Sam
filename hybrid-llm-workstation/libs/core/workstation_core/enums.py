"""Canonical state machines shared by every service (spec sections 8, 12, 17)."""

from enum import StrEnum


class Environment(StrEnum):
    LOCAL = "local"
    CLOUD = "cloud"


class ModelStatus(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class GPUStatus(StrEnum):
    OFF = "OFF"
    PROVISIONING = "PROVISIONING"
    STARTING = "STARTING"
    BOOTING = "BOOTING"
    READY = "READY"
    BUSY = "BUSY"
    IDLE = "IDLE"
    STOPPING = "STOPPING"
    ERROR = "ERROR"


# Legal transitions for the GPU state machine (spec section 8). Any transition
# not listed here is rejected by GPULifecycleManager._transition().
GPU_TRANSITIONS: dict[GPUStatus, set[GPUStatus]] = {
    GPUStatus.OFF: {GPUStatus.PROVISIONING, GPUStatus.STARTING},
    GPUStatus.PROVISIONING: {GPUStatus.STARTING, GPUStatus.ERROR},
    GPUStatus.STARTING: {GPUStatus.BOOTING, GPUStatus.ERROR, GPUStatus.STOPPING},
    GPUStatus.BOOTING: {GPUStatus.READY, GPUStatus.ERROR, GPUStatus.STOPPING},
    GPUStatus.READY: {GPUStatus.BUSY, GPUStatus.IDLE, GPUStatus.STOPPING, GPUStatus.ERROR},
    # BUSY -> STOPPING is only ever taken via an explicit force-stop
    # (spec: "never terminate active inference" unless the user overrides).
    GPUStatus.BUSY: {GPUStatus.READY, GPUStatus.IDLE, GPUStatus.ERROR, GPUStatus.STOPPING},
    GPUStatus.IDLE: {GPUStatus.BUSY, GPUStatus.STOPPING, GPUStatus.ERROR},
    GPUStatus.STOPPING: {GPUStatus.OFF, GPUStatus.ERROR},
    GPUStatus.ERROR: {GPUStatus.STOPPING, GPUStatus.OFF, GPUStatus.STARTING},
}

# States in which it is unsafe to stop the GPU (spec section 8: "never
# terminate active inference").
GPU_PROTECTED_STATES = {GPUStatus.BUSY, GPUStatus.STARTING, GPUStatus.BOOTING, GPUStatus.PROVISIONING}


class TaskStatus(StrEnum):
    QUEUED = "QUEUED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    PAUSED = "PAUSED"
    REQUIRES_APPROVAL = "REQUIRES_APPROVAL"
    RETRYING = "RETRYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


# Legal transitions for the task state machine (spec section 12). A failure
# with retries remaining goes to RETRYING then back to QUEUED rather than
# ever touching FAILED, so FAILED stays a genuine terminal state reached
# only once retries are exhausted.
TASK_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.QUEUED: {TaskStatus.STARTING, TaskStatus.CANCELLED, TaskStatus.PAUSED},
    TaskStatus.STARTING: {TaskStatus.RUNNING, TaskStatus.FAILED, TaskStatus.CANCELLED, TaskStatus.RETRYING},
    TaskStatus.RUNNING: {
        TaskStatus.WAITING, TaskStatus.REQUIRES_APPROVAL, TaskStatus.PAUSED,
        TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED, TaskStatus.RETRYING,
    },
    TaskStatus.WAITING: {TaskStatus.RUNNING, TaskStatus.FAILED, TaskStatus.CANCELLED, TaskStatus.RETRYING},
    TaskStatus.PAUSED: {TaskStatus.QUEUED, TaskStatus.CANCELLED},
    TaskStatus.REQUIRES_APPROVAL: {TaskStatus.RUNNING, TaskStatus.CANCELLED, TaskStatus.FAILED},
    TaskStatus.RETRYING: {TaskStatus.QUEUED, TaskStatus.CANCELLED},
    TaskStatus.COMPLETED: set(),
    TaskStatus.FAILED: set(),
    TaskStatus.CANCELLED: set(),
}

TASK_TERMINAL_STATES = {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}
TASK_ACTIVE_STATES = {
    TaskStatus.QUEUED,
    TaskStatus.STARTING,
    TaskStatus.RUNNING,
    TaskStatus.WAITING,
    TaskStatus.PAUSED,
    TaskStatus.REQUIRES_APPROVAL,
    TaskStatus.RETRYING,
}


class TaskType(StrEnum):
    CHAT = "chat"
    GENERATE = "generate"
    EXECUTION = "execution"


class ApprovalStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    EXPIRED = "EXPIRED"


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class PolicyLevel(StrEnum):
    RESTRICTED = "RESTRICTED"
    APPROVAL = "APPROVAL"
    TRUSTED = "TRUSTED"


class ExecutionStatus(StrEnum):
    PENDING = "PENDING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    DENIED = "DENIED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class NotificationStatus(StrEnum):
    UNREAD = "unread"
    READ = "read"


class NotificationType(StrEnum):
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_REQUIRES_APPROVAL = "task_requires_approval"
    GPU_STARTED = "gpu_started"
    GPU_STOPPED = "gpu_stopped"
    GPU_ERROR = "gpu_error"
    WORKER_UNAVAILABLE = "worker_unavailable"
    COST_LIMIT_REACHED = "cost_limit_reached"
