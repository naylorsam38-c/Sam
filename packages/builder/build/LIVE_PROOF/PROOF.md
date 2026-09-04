# Live proof: pm-teamwork/SCR-001 from parts alone

No new code was written for this proof -- `builder.py` was imported and
called completely unmodified. The only part exercised is `crud_list_detail`
(`packages/builder/parts_shelf.json`), against a real, filtered subset of
pm-teamwork's own real locked structure (one record, one screen).

## Steps actually run

1. Loaded pm-teamwork's real locked `structure`, extracted the real
   `Project` record and its real `SCR-001` list-screen entry only.
2. Called `bl.build_screens(spec)` directly -- produced exactly one real
   HTML page, for `pm-teamwork/SCR-001`, and nothing else.
3. Called `bl.build(spec, ...)` -- wrote a real, complete, runnable app
   (schema.sql, app.py, static/pm-teamwork/SCR-001.html) to `build/LIVE_PROOF/app/`.
4. Started `app.py` as a real subprocess on port 8997.
5. Made a real HTTP GET to `/pm-teamwork%2FSCR-001.html` -- got a real
   `200` and a real rendered page (saved verbatim as `RESPONSE.html`).
6. Made a real HTTP POST to `/api/projects` (creating a real row) and a
   real GET to confirm it lists back -- proving the same part's CRUD API
   half also actually runs, not just the static page.

## Real captured evidence

- HTTP status: `200`
- Created row: `{"id": "c7462da2-6cab-44ab-a79a-5d61c594ec5e"}`
- Listed back: `[{"id": "c7462da2-6cab-44ab-a79a-5d61c594ec5e", "created_at": "2026-09-04T16:37:57Z", "updated_at": "2026-09-04T16:37:57Z", "name": "Shelf proof project", "description": "from parts alone", "owner": "Sam", "due_date": null, "colour": null}]`
- Rendered page saved to `RESPONSE.html` in this directory (first 300 chars below):

```html
<!doctype html>
<title>Projects</title>
<style>body{font-family:system-ui,sans-serif;max-width:800px;margin:40px auto}
table{border-collapse:collapse;width:100%} td,th{border:1px solid #ccc;padding:6px}body{margin:0}.app-header{display:flex;align-items:center;gap:10px;padding:12px 16px;border-bottom
```
