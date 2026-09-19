# Walkthrough — Memos for Notes/knowledge

Repo https://github.com/usememos/memos @ `7e3d3c63156c206209fdc8e75a4fb117b1aaf1fb`  
Started 2026-09-19T05:43:39, finished 2026-09-19T05:44:20

## Boot: **BOOTED**

- recipe: scripts/compose.yaml
- url: http://127.0.0.1:5230/
- detail: UI answered at http://127.0.0.1:5230/ (memos published 5230->5230)

## Getting in: **IN**

- landing: `http://127.0.0.1:5230/auth?redirect=%2F` → screenshots/01_landing.png
- login as admin/admin → http://127.0.0.1:5230/ → screenshots/02_gate_step_1.png
- after: `http://127.0.0.1:5230/` → screenshots/03_after_gate.png

## Capabilities

| Capability | Verdict | Evidence | Screenshot |
|---|---|---|---|
| Pages | **ABSENT** |  |  |
| blocks | **ABSENT** |  |  |
| rich text | **ABSENT** |  |  |
| databases | **ABSENT** |  |  |
| tables | **ABSENT** |  |  |
| views | **ABSENT** |  |  |
| search | **SEEN** | words ['search'] on visited pages; no dedicated screen reached |  |
| sharing | **ABSENT** |  |  |
| comments | **ABSENT** |  |  |
| templates | **ABSENT** |  |  |
| permissions | **ABSENT** |  |  |

## Summary: booted=True gate=IN reached 0/11, seen 1, absent 10

Gaps (to be filled by capability services): Pages, blocks, rich text, databases, tables, views, sharing, comments, templates, permissions, search
