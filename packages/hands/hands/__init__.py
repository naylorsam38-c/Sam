"""Hands — the paperwork-execution engine.

The customer buys a job, not an agent: a session is bound to a defined
workflow, and the engine executes only what that workflow permits. Missing
information is asked for, never guessed; anything that makes a declaration
in the customer's name stops at the Trust Gate, which is enforced in the
backend against the exact payload about to be executed.

Built on the Builder's parts shelf (pdf_form_filling, document_signing,
audit_trail) at their real locations — see `shelf.py`.
"""

from . import config, documents, engine, fields, provenance, session, shelf, store, trust_gate, workflow

__all__ = ["config", "documents", "engine", "fields", "provenance", "session", "shelf",
           "store", "trust_gate", "workflow"]
