# The workflow-node vocabulary (CAP-0038..CAP-0077)

A second, separate target list alongside `CAPABILITY_VOCABULARY.md`'s
81-name app-feature vocabulary. Where that list is end-user app
*features* ("book slot", "place bid"), this one is workflow/automation
*node types* — the building blocks of an n8n/Zapier-style integration
library (HTTP Request, Parse JSON, Send Email, Loop, ...).

Source: Sam's 100-name node-capability list, narrowed to the
"first-release priority" ~40 he named explicitly. Same rule as the
81-name list: fixed target, worked through name by name, never padded
or substituted with a similar-sounding name. Never invented, never
mocked — every entry here still goes through the same real pipeline
(discover a real, license-clear app -> AST-confirm a real attach point
-> harvest with provenance -> compose a real running build -> prove it
live) as CAP-0001..0037, reusing an already-discovered, already
license-cleared app wherever a genuine match exists there, and only
discovering a new app when the operation is a real integration none of
the 24 existing apps happen to implement (e.g. no app here calls
Twilio or an LLM API).

```
CAP-0038  webhook trigger              CAP-0058  find and replace
CAP-0039  schedule trigger             CAP-0059  regular expression matcher
CAP-0040  manual trigger               CAP-0060  date formatting
CAP-0041  HTTP request (call API)      CAP-0061  mathematical calculation
CAP-0042  conditional branch           CAP-0062  send email
CAP-0043  loop (loop over items)       CAP-0063  send SMS
CAP-0044  delay / wait                 CAP-0064  send chat message
CAP-0045  error handling               CAP-0065  upload file
CAP-0046  create database record       CAP-0066  download file
CAP-0047  read database records        CAP-0067  generate PDF
CAP-0048  update database record       CAP-0068  AI text generation
CAP-0049  delete database record       CAP-0069  AI text summarization
CAP-0050  filter records               CAP-0070  AI text classification
CAP-0051  map fields                   CAP-0071  AI text extraction
CAP-0052  merge data                   CAP-0072  OCR
CAP-0053  parse JSON                   CAP-0073  authentication
CAP-0054  create JSON                  CAP-0074  API key handling
CAP-0055  parse CSV                    CAP-0075  OAuth connection
CAP-0056  create CSV                   CAP-0076  logging
CAP-0057  text template                CAP-0077  retry
```

Note: Sam's source list had both "Error handling" (workflow-control
category) and "Error handler" (first-release-priority list) as two
entries for what is the same node type; merged into one, CAP-0045.

## Status (0 harvested, 40 remaining)

Not yet researched: everything above. Two research passes are running
now: (1) a source-grep across the 24 already-cloned, already
license-cleared apps for genuine existing attach points for the
technical/generic node types (HTTP request, JSON/CSV parse+create,
regex, date formatting, math, templating, find/replace, merge, retry,
logging, error handling, conditional branch, loop, delay, database
CRUD, file upload/download, PDF generation, email, auth, API keys);
(2) new-app discovery for the node types that genuinely need a fresh
real integration none of the 24 apps happen to implement (webhook
trigger, schedule trigger, send SMS, send chat message, the four AI
text operations, OCR, OAuth connection).

This file's status section is updated as each CAP-ID is actually
harvested and proven — same discipline as `CAPABILITY_VOCABULARY.md`:
"300 discovered ≠ 300 proven."
