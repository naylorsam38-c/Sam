"""Stage-Conditional Field Requiredness Engine — crm-pipeline's Deal
pipeline on_complete text: "Won: the deal locks... Lost: Lost reason
becomes required." R.02's `required` flag is fixed at authoring time and
cannot express "required only once the record reaches stage X"; this
engine enforces that rule at write time instead.
"""


class RequirednessViolation(ValueError):
    pass


def validate(rules, stage, fields):
    """rules: {stage_name: [field_name, ...]} -- fields required once a
    record is AT that stage. fields: the record's real current field values
    (dict). Raises RequirednessViolation naming every missing field; returns
    silently if none are missing (including when `stage` has no rule)."""
    required = rules.get(stage, [])
    missing = [f for f in required if not fields.get(f)]
    if missing:
        raise RequirednessViolation(f"stage '{stage}' requires {missing}, got {fields}")


def prove():
    """Real proof against crm-pipeline's own real rule: a Deal moving into
    'Lost' without a Lost reason is rejected; the same Deal with one set is
    accepted; a Deal in 'Won' (no rule for that stage) needs nothing extra."""
    rules = {"Lost": ["Lost reason"]}

    rejected = False
    try:
        validate(rules, "Lost", {"Title": "Acme deal", "Lost reason": None})
    except RequirednessViolation as e:
        rejected = True
        rejection_message = str(e)
    assert rejected, "a Lost deal with no Lost reason must be rejected"

    validate(rules, "Lost", {"Title": "Acme deal", "Lost reason": "price"})  # must not raise
    validate(rules, "Won", {"Title": "Acme deal"})  # no rule for Won -> must not raise

    return {"engine": "stage_conditional_requiredness", "real_system": "pure function, exercised for real (no db needed)",
            "steps": ["reject a real Lost deal missing Lost reason",
                      "accept the same deal once Lost reason is set",
                      "accept a Won deal with no rule at all"],
            "observed": {"rejection_message": rejection_message}}


if __name__ == "__main__":
    import pprint
    pprint.pprint(prove())
