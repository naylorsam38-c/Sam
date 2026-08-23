# Spec Writer — Component 2b

Drop-in add-on for Spec Builder.

## Contract

```text
raw transcript
    -> Extract
    -> Gap Scan
    -> Draft
    -> specs/drafts/<slug>-<n>.yaml
    -> existing specgate.py
    -> exit 0 (approved) / 3 (questions)
```

`specgate.py` is not modified.

The writer is deliberately split into three model calls:

1. Extract: statements only.
2. Gap scan: gaps only.
3. Draft: template output, with `[ASK]` for every gap.

The writer never declares a spec complete.

## Requirements

- Python 3.10+
- PyYAML
- An OpenAI-compatible chat-completions endpoint, or a custom `ModelClient`.
- The existing `specgate.py` and `schema/spec.template.yaml` remain outside this package.

Install:

```bash
pip install pyyaml
```

## CLI

```bash
python -m spec_writer \
  --transcript path/to/transcript.txt \
  --template schema/spec.template.yaml \
  --rules specgate_rules.txt \
  --gate specgate.py \
  --slug my-idea
```

The command writes:

```text
specs/transcripts/my-idea.txt
specs/drafts/my-idea-1.yaml
```

Revision numbering never overwrites an existing draft.

Environment variables for the default model client:

```text
SPEC_WRITER_MODEL
SPEC_WRITER_BASE_URL
SPEC_WRITER_API_KEY
SPEC_WRITER_MODEL_TIMEOUT
```

The default endpoint is OpenAI-compatible. A custom provider can be supplied by importing and implementing `ModelClient`.

## Gate exit codes

- `0`: valid / complete
- `3`: valid structure with `[ASK]` questions
- `2`: structurally broken writer output

The writer itself raises on structural failures before handing the file to the gate.

## Important

The package does not contain or replace your project's twelve rules or template. It reads those from the paths supplied at runtime.
