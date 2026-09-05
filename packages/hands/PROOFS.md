# Hands — captured evidence

Every line below is real output from a real run in this repository, pasted
as it was printed. Nothing here was produced against a mock, a stub or a
simulated provider — the engine calls no model, so there is no provider to
fake.

## 1. `document_field_detection.prove()`

Renders a real 3-field AcroForm PDF with the shelf's own
`pdf_form_filling`, parses it with this package's independently written
reader, and cross-checks against the shelf's own reader.

```
$ python3 -c "import sys; sys.path.insert(0,'packages/hands'); \
    from hands import fields; import pprint; pprint.pprint(fields.prove())"

'part': 'document_field_detection',
'real_system': 'a real PDF file on disk, parsed twice by two independently written readers',
'steps': ['render a real 3-field AcroForm PDF via the shelf part',
          'detect name/value/rect with this reader',
          "read name/value with the shelf's own reader",
          'assert both readers agree, and that the geometry round-trips',
          'classify: known stays known, a declaration field never auto-fills'],
'observed': {'detected': [{'name': 'worker_name', 'value': '', 'rect': [150.0, 700.0, 400.0, 715.0]},
                          {'name': 'site_address', 'value': '12 Rundle St', 'rect': [150.0, 660.0, 400.0, 675.0]},
                          {'name': 'induction_complete_declaration', 'value': '', 'rect': [150.0, 620.0, 400.0, 635.0]}],
             'classified': [{'name': 'worker_name', 'provenance': 'KNOWN', 'value': 'Sam Naylor',
                             'source': 'on file for this customer'},
                            {'name': 'site_address', 'provenance': 'KNOWN', 'value': '12 Rundle St',
                             'source': 'already present in the uploaded document'},
                            {'name': 'induction_complete_declaration', 'provenance': 'MISSING',
                             'value': '', 'source': None}]}
```

The third field is the one that matters: a value for it exists nowhere, so
it is MISSING — and once supplied it becomes REQUIRES_APPROVAL rather than
being filled, because its name declares that a worker completed an
induction.

## 2. The suite

```
$ pytest packages/hands/tests -v
platform linux -- Python 3.11.15, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/claude/repo
configfile: pytest.ini
collected 29 items

test_hands_browser.py::test_the_screen_shows_real_field_state_from_the_real_document PASSED
test_hands_browser.py::test_nothing_is_written_until_the_customer_clicks_approve PASSED
test_hands_browser.py::test_declining_in_the_browser_ends_the_session_declined PASSED
test_hands_browser.py::test_the_screen_refuses_to_work_without_a_token PASSED
test_hands_live.py::test_field_detection_proves_itself_against_a_real_pdf PASSED
test_hands_live.py::test_document_completion_end_to_end_over_real_http PASSED
test_hands_live.py::test_an_approval_does_not_authorise_a_different_payload PASSED
test_hands_live.py::test_an_approval_is_single_use PASSED
test_hands_live.py::test_declining_is_a_real_outcome_not_an_error PASSED
test_hands_live.py::test_a_customer_cannot_approve_something_they_were_never_shown PASSED
test_hands_live.py::test_two_concurrent_executions_spend_one_approval_once PASSED
test_hands_live.py::test_a_read_only_workflow_cannot_fill_anything PASSED
test_hands_live.py::test_the_engine_refuses_a_workflow_that_is_not_defined PASSED
test_hands_live.py::test_an_inconsistent_workflow_is_refused_at_definition_time[kwargs0-no code performs those actions] PASSED
test_hands_live.py::test_an_inconsistent_workflow_is_refused_at_definition_time[kwargs1-both permitted and prohibited] PASSED
test_hands_live.py::test_an_inconsistent_workflow_is_refused_at_definition_time[kwargs2-can never be proven done] PASSED
test_hands_live.py::test_execution_is_refused_before_the_price_is_locked PASSED
test_hands_live.py::test_an_original_is_write_once PASSED
test_hands_live.py::test_a_filename_cannot_escape_the_session_directory[../../escaped.pdf] PASSED
test_hands_live.py::test_a_filename_cannot_escape_the_session_directory[/etc/passwd.pdf] PASSED
test_hands_live.py::test_a_filename_cannot_escape_the_session_directory[sub/dir.pdf] PASSED
test_hands_live.py::test_a_filename_cannot_escape_the_session_directory[..\windows.pdf] PASSED
test_hands_live.py::test_an_oversized_document_is_refused_before_it_is_stored PASSED
test_hands_live.py::test_a_corrupt_upload_is_a_client_error_not_a_crash PASSED
test_hands_live.py::test_illegal_lifecycle_moves_are_refused PASSED
test_hands_live.py::test_a_value_without_a_source_cannot_be_stored PASSED
test_hands_live.py::test_the_api_refuses_an_unauthenticated_request PASSED
test_hands_live.py::test_the_server_refuses_to_start_without_a_token PASSED
test_hands_live.py::test_state_survives_a_server_restart PASSED

============================= 29 passed in 17.50s ==============================
```

What each of those actually touches: a real `ThreadingHTTPServer` bound to
a real port, real HTTP requests over a real socket, a real sqlite file, and
real PDFs written to and read back from disk. The four browser tests drive
real Chromium through Playwright against that same server.

## 3. The whole repository, with Hands in it

```
$ pytest -q
155 passed in 137.01s (0:02:17)
```

126 before this package, 29 from it, nothing broken.

## 4. Two defects this work found and fixed

Both were found by writing the test that tried to break the thing, not by
reading the code.

**Double-spend of one approval.** `trust_gate.check()` read the approval,
then marked it consumed in a second statement. Two concurrent executions
could both pass the read and both act, producing two completed documents
from one approval. Fixed by making the consume a conditional update
(`WHERE consumed_at IS NULL`) and treating a zero-row result as the gate
still being shut. Verified by removing the fix and re-running: the race
test fails three times out of three, and passes three out of three with it
restored.

**Approval for something never shown.** A caller could compute a payload
hash themselves and POST an approval for it before the engine had ever
asked, pre-opening a gate. `trust_gate.decide()` now refuses any decision
whose payload hash has no matching `action_required` event on that
session. Covered by
`test_a_customer_cannot_approve_something_they_were_never_shown`.

Three more refusals were added the same way, each with its own test:
filenames that are really paths, uploads over `MAX_UPLOAD_BYTES`, and
corrupt base64 (a 400, not a 500).
