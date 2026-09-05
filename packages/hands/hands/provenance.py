"""Where every value came from.

The product rule this enforces: missing information is asked for, never
guessed. A value therefore cannot exist in a session without a provenance
and, where the provenance is DERIVED, without naming the real values it
was derived from. There is deliberately no "assumed" or "default"
provenance — a value with no source is MISSING, and MISSING stops
execution.
"""

KNOWN = "KNOWN"                              # already on file for this customer
SUPPLIED_BY_CUSTOMER = "SUPPLIED_BY_CUSTOMER"  # the customer typed it, this session
DERIVED = "DERIVED"                          # computed from other real values
MISSING = "MISSING"                          # not known — must be asked for
REQUIRES_APPROVAL = "REQUIRES_APPROVAL"      # known, but declaring it needs the customer

ALL = (KNOWN, SUPPLIED_BY_CUSTOMER, DERIVED, MISSING, REQUIRES_APPROVAL)

#: Provenances whose value may be written into a document without stopping.
FILLABLE = (KNOWN, SUPPLIED_BY_CUSTOMER, DERIVED)

#: Provenances that stop execution and hand control back to the customer.
BLOCKING = (MISSING, REQUIRES_APPROVAL)


class ProvenanceError(ValueError):
    pass


def check(provenance, value, source=None):
    """Validates one value/provenance pair. Raises rather than repairing:
    a value the engine cannot account for must not enter a session."""
    if provenance not in ALL:
        raise ProvenanceError(f"unknown provenance {provenance!r} — must be one of {list(ALL)}")
    if provenance == MISSING:
        if value not in (None, ""):
            raise ProvenanceError("a MISSING value must be empty — it is the absence of a value")
        return
    if value in (None, ""):
        raise ProvenanceError(f"provenance {provenance} claims a value, but the value is empty")
    if provenance == DERIVED and not source:
        raise ProvenanceError("a DERIVED value must name what it was derived from")
    if provenance == SUPPLIED_BY_CUSTOMER and not source:
        raise ProvenanceError("a customer-supplied value must record who supplied it")


def blocks_execution(provenance):
    return provenance in BLOCKING
