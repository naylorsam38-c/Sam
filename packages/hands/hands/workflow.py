"""Workflow definitions — the object the engine executes.

The architectural rule this file exists to enforce: the engine never
receives a customer command. It receives a Workflow, which names exactly
which actions are permitted, which are prohibited, which stop for the
customer's approval, and what counts as finished. A workflow that is
internally inconsistent is refused here, at definition time, so an
inconsistent one can never reach execution.
"""

from . import config


class WorkflowError(ValueError):
    """A workflow definition that must not be allowed to execute."""


class Workflow:
    def __init__(self, workflow_id, name, permitted_actions, prohibited_actions=(),
                 approval_gates=(), completion_conditions=(), modules=()):
        self.workflow_id = workflow_id
        self.name = name
        self.permitted_actions = tuple(permitted_actions)
        self.prohibited_actions = tuple(prohibited_actions)
        self.approval_gates = tuple(sorted(set(approval_gates) | set(config.ALWAYS_GATED_ACTIONS)))
        self.completion_conditions = tuple(completion_conditions)
        self.modules = tuple(modules)
        self._validate()

    def _validate(self):
        if not self.workflow_id:
            raise WorkflowError("a workflow must have an id")
        if not self.permitted_actions:
            raise WorkflowError(f"{self.workflow_id}: a workflow that permits nothing cannot execute")

        unknown = [a for a in self.permitted_actions if a not in config.KNOWN_ACTIONS]
        if unknown:
            raise WorkflowError(
                f"{self.workflow_id}: permits {unknown} — no code performs those actions. "
                f"Known actions: {list(config.KNOWN_ACTIONS)}")

        both = sorted(set(self.permitted_actions) & set(self.prohibited_actions))
        if both:
            raise WorkflowError(f"{self.workflow_id}: {both} is both permitted and prohibited")

        ungated = [a for a in config.ALWAYS_GATED_ACTIONS
                   if a in self.permitted_actions and a not in self.approval_gates]
        if ungated:  # defensive: the constructor unions them in, so this cannot normally fire
            raise WorkflowError(f"{self.workflow_id}: {ungated} must be gated")

        stray = [a for a in self.approval_gates
                 if a not in self.permitted_actions and a in config.KNOWN_ACTIONS
                 and a not in config.ALWAYS_GATED_ACTIONS]
        if stray:
            raise WorkflowError(f"{self.workflow_id}: gates {stray}, which it does not permit")

        if not self.completion_conditions:
            raise WorkflowError(
                f"{self.workflow_id}: a workflow with no completion conditions can never be proven done")

    def permits(self, action):
        return action in self.permitted_actions and action not in self.prohibited_actions

    def requires_approval(self, action):
        return action in self.approval_gates

    def to_dict(self):
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "modules": list(self.modules),
            "permitted_actions": list(self.permitted_actions),
            "prohibited_actions": list(self.prohibited_actions),
            "approval_gates": list(self.approval_gates),
            "completion_conditions": list(self.completion_conditions),
        }


# ---------------------------------------------------------------------
# The workflows that actually exist. A workflow not in this registry
# cannot be run: the engine looks a session's workflow up by id here.
# ---------------------------------------------------------------------

DOCUMENT_COMPLETION = Workflow(
    workflow_id="document_completion",
    name="Document completion",
    modules=("document_intake", "field_detection", "field_fill", "completed_copy"),
    permitted_actions=("read_document", "fill_field", "generate_completed", "sign_completed"),
    prohibited_actions=(),
    approval_gates=("generate_completed", "sign_completed"),
    completion_conditions=(
        "every detected field is either filled or explicitly waived by the customer",
        "a completed copy exists as a separate file from the original",
        "the original document's bytes are unchanged",
        "the completed copy carries an attestation over its real bytes",
    ),
)

READ_ONLY_REVIEW = Workflow(
    workflow_id="read_only_review",
    name="Read-only document review",
    modules=("document_intake", "field_detection"),
    permitted_actions=("read_document",),
    prohibited_actions=("fill_field", "generate_completed", "sign_completed"),
    approval_gates=(),
    completion_conditions=("every field in the document has been listed back to the customer",),
)

REGISTRY = {w.workflow_id: w for w in (DOCUMENT_COMPLETION, READ_ONLY_REVIEW)}


def get(workflow_id):
    try:
        return REGISTRY[workflow_id]
    except KeyError:
        raise WorkflowError(
            f"no such workflow {workflow_id!r} — defined workflows are {sorted(REGISTRY)}") from None
