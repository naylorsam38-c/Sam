"""Hands — editable rules block.

Everything you can safely tune lives in this file. Change a value here and
the engine changes behaviour; you never have to read the code underneath.
Each setting says what it does and what changes if you alter it.
"""

# =====================================================================
# RULES / CONFIG  — edit these, nothing below them
# =====================================================================

# Where session databases and stored documents live. Change this to move
# every session's data somewhere else. Nothing outside this directory is
# ever written to.
DATA_ROOT = "hands-data"

# The action names Hands is allowed to perform at all, engine-wide. A
# workflow may permit a subset of these and no more. Add a name here only
# when the code to perform it actually exists -- an unknown action is
# refused at workflow-definition time, not at execution time.
KNOWN_ACTIONS = (
    "read_document",      # parse a stored document and list its real fields
    "fill_field",         # write one real value into one real field
    "generate_completed", # write the completed copy as a NEW file
    "sign_completed",     # HMAC-attest the completed copy's real bytes
)

# Actions that ALWAYS require the customer's recorded approval before they
# run, no matter what a workflow says. Removing a name from this tuple
# lets that action run unattended; adding one makes it stop and ask. This
# is the backend half of the Trust Gate -- a frontend button alone is not
# authorisation.
ALWAYS_GATED_ACTIONS = (
    "generate_completed",
    "sign_completed",
)

# Field names (matched case-insensitively, as substrings) that Hands must
# never fill on its own, even when a value is known, because filling one
# makes a declaration in the customer's name. Every one of these routes
# through the Trust Gate instead. Remove an entry and Hands will fill that
# field automatically -- consider what you are declaring on someone's
# behalf before you do.
DECLARATION_FIELD_MARKERS = (
    "signature",
    "declaration",
    "declare",
    "consent",
    "certif",     # certificate / certification / certified
    "i_agree",
    "competen",   # competency / competent
    "induction_complete",
)

# How long an approval stays valid, in seconds, measured from when the
# customer approved. Raise it to give slower customers longer; lower it to
# force a fresh approval closer to execution. An expired approval is
# treated as no approval at all.
APPROVAL_TTL_SECONDS = 60 * 60 * 24

# Whether the price must be locked before a session may execute. True
# means a session with no locked price is refused at the READY gate (the
# customer-facing product). Set False for the operator path (Command Desk
# delegating to Hands), where there is no pricing layer at all.
REQUIRE_PRICE_LOCK = True

# How much the quoted price may rise, as a fraction, before execution
# stops and re-quotes instead of silently continuing. 0.0 means any
# increase at all stops execution.
PRICE_TOLERANCE = 0.0

# The largest document Hands will accept, in bytes. Raise it if your
# customers upload bigger files; anything over the limit is refused at
# intake rather than half-stored.
MAX_UPLOAD_BYTES = 25 * 1024 * 1024

# Whether the HTTP API requires a bearer token. True means every request
# without a matching Authorization header is refused with 401. Set False
# only for a local run you are driving yourself.
REQUIRE_AUTH = True

# The environment variable holding that token. Set HANDS_API_TOKEN before
# starting the server; with REQUIRE_AUTH on and no token set, the server
# refuses to start rather than serving an open API.
API_TOKEN_ENV_VAR = "HANDS_API_TOKEN"

# The secret used to attest completed documents. Real deployments must set
# HANDS_SIGNING_SECRET in the environment; the fallback below exists so
# the engine runs on a fresh checkout, and is not a production secret.
SIGNING_SECRET_ENV_VAR = "HANDS_SIGNING_SECRET"
SIGNING_SECRET_FALLBACK = "hands-dev-attestation-secret"

# =====================================================================
# END OF RULES — implementation below
# =====================================================================

import os


def signing_secret():
    """The real secret used to attest completed documents."""
    return os.environ.get(SIGNING_SECRET_ENV_VAR) or SIGNING_SECRET_FALLBACK


def is_declaration_field(field_name):
    """True when this field name makes a declaration in the customer's
    name and therefore may never be filled without approval."""
    lowered = field_name.lower()
    return any(marker in lowered for marker in DECLARATION_FIELD_MARKERS)
