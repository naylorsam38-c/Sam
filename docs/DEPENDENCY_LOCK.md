# Dependency Lock + Licence Manifest & Audit Gate

This is the machine-enforced half of the licensing policy (the human-readable
half is `LICENSING_REGISTER.md`). It exists to make "licensing verified" a
*checked* claim, never a spoken one.

## Files
- `config/dependency_lock.yaml` — one entry per component with the mandatory
  fields: **repo URL, commit hash, package version, model-weight filename,
  SHA-256, code licence, weight licence**, plus `dynamic_download` /
  `download_source` / `kind` / `ship`.
- `scripts/licence_audit.py` — the gate. Run `python scripts/licence_audit.py`
  or `make audit`.

## Exit codes (build gate)
| Code | Status | Meaning |
|---|---|---|
| 0 | **PASS** | every shipping component pinned + hashed + licence-approved. Only now may the repo be called "licensing verified". |
| 1 | **PENDING** | no hard violation, but `PIN_ME` commits / missing SHA-256 remain. **Not** licensing-verified. |
| 2 | **FAIL** | a hard rule was violated; the build must stop. |

## Hard-fail rules (each → exit 2)
1. a shipping dependency has **no licence**;
2. **code licence and model-weight licence differ** and either is unapproved;
3. a model **downloads weights dynamically from an unverified source**;
4. a **test asset / dataset is non-commercial** and is shipped;
5. **InsightFace** weights appear anywhere (manifest, file tree, installed pkgs);
6. **CodeFormer, XTTS(-v2) or Wav2Lip** appear anywhere, including transitively
   (checked against requirements files and `pip freeze`, exact-token match).

## Why the default manifest currently reports FAIL (intended)
Out of the box the audit **fails on purpose**, proving the gate is real:
- `faster-whisper` and `gfpgan` fetch weights dynamically by default → **Rule 3**.
  Fix on the build host: pre-download the exact weights, record the SHA-256, set
  `dynamic_download: false`, `download_source: verified`, and load with
  `local_files_only`.
- Every `PIN_ME` commit and missing `sha256` keeps the status at **PENDING** even
  after the FAILs are cleared.

## Reaching PASS (the audit checklist)
1. On the GPU build host, clone each repo at a fixed commit; fill `commit`.
2. Download each weight; fill `weight_file` + `sha256` (`sha256sum <file>`).
3. Set `dynamic_download: false` + `download_source: verified` once weights are
   local and pinned.
4. Remove InsightFace pretrained models from LivePortrait; confirm YuNet is the
   detector. Verify no InsightFace/CodeFormer/XTTS/Wav2Lip in `pip freeze`.
5. Do **not** copy MuseTalk's test data into the image (`ship: false` stays true).
6. Run `make audit` until it prints `STATUS: PASS` (exit 0).
7. Only then update any status badge to "licensing verified".

## Transitive scope
The audit also scans `requirements*.txt` and `pip freeze` for the forbidden
package tokens, so a banned component pulled in **as a sub-dependency** is caught.
For a fully airtight transitive audit, generate a complete lockfile
(`pip-compile`/`pip freeze > requirements.lock`) on the build host and re-run the
gate against it, and repeat for the Node/Dart client trees.
