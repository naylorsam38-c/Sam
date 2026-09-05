# Integration

This add-on intentionally does not edit the existing Spec Builder.

## 1. Copy

Copy the `spec_writer/` directory into the project root, or install the
package with:

```bash
pip install -e /path/to/spec_writer_addon
```

## 2. Keep existing files authoritative

Continue using the project's:

```text
schema/spec.template.yaml
specgate.py
```

Provide the path to the project's rules file. If the twelve rules currently
live inside `specgate.py`, export them to a plain text rules file for the
writer rather than making the writer import gate internals.

## 3. Run

```bash
python -m spec_writer \
  --transcript specs/transcripts/my-idea.txt \
  --template schema/spec.template.yaml \
  --rules specgate_rules.txt \
  --gate specgate.py \
  --slug my-idea
```

The writer creates a new revision:

```text
specs/drafts/my-idea-1.yaml
specs/drafts/my-idea-2.yaml
...
```

It never overwrites an existing revision.

## 4. Existing gate remains the authority

The writer validates its own structural contract first, then invokes the
existing gate.

Allowed gate results:

```text
0 = approved
3 = open questions
```

A gate result of `2` or any other unexpected result is treated as an error.

## 5. Three-call invariant

A normal write pass makes exactly three calls to `ModelClient.call()`:

1. Extract
2. Gap Scan
3. Draft

No combined prompt is used.

## 6. Revision loop

When Sam answers `[ASK]` questions, the caller should invoke Spec Writer again
with the new complete transcript or the previous draft plus the answers,
depending on the surrounding Spec Builder contract.

The add-on accepts `prior_spec` and `answers` as programmatic inputs through
`SpecWriter.write()`. The CLI intentionally keeps the first integration
surface small.

## 7. Provider boundary

`ModelClient` is a protocol. If the project already has a model abstraction,
adapt it to:

```python
class MyClient:
    def call(self, system: str, user: str) -> str:
        ...
```

Then:

```python
writer = SpecWriter(config, client=MyClient())
```

No other part of Spec Writer needs to know which model is used.
