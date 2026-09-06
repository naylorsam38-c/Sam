# DRAFT — step 4 brief (model step)

The task is to fill the fixed field set (schema/spec.template.yaml) from the
EXTRACT output and the GAP SCAN output, and to author the packet split.

## Rules
- Every field filled from an extracted item cites nothing new; every gap from
  the GAP SCAN appears as its [ASK] marker verbatim, in the field it blocks.
  Never answer an [ASK] yourself. Never substitute a placeholder.
- Acceptance criteria: each `check` names an observable; each `verify` is a
  runnable command the builder does not control. The banned words
  (works, correct, properly, good, reliable, robust, user-friendly, clean,
  appropriate, as expected, seamless, intuitive, handles gracefully) will be
  rejected mechanically — do not use them. If a criterion cannot be written
  mechanically, label it `human: true` rather than faking a command.
- Every control on every surface names an endpoint or `type: display_only`.
  There is no third option.
- At most seven constraints. If the build needs more, stop and report that
  the spec must be split — do not drop constraints silently.
- Packets: one packet, one job; inputs inline (a packet that would need
  another packet's output is a wrong split — merge, or pass the value in
  inputs and declare depends_on); every machine AC assigned to exactly one
  packet; independent packets left parallel.
- If the gate returns failures (a JSON list of rule ids and offending lines),
  fix exactly those lines and nothing else.

## Output
One YAML document conforming to schema/spec.template.yaml, status: draft.
