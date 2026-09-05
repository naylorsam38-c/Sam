# Universal App Crawler

A reusable deterministic smoke-test harness for web apps.

It does **not** assume your application's architecture. Give it a starting URL and it will:

- crawl reachable HTTP(S) pages
- optionally restrict crawling to the starting origin
- record HTTP/navigation failures
- capture browser console errors and page errors
- detect failed network requests
- enumerate visible buttons
- click non-destructive buttons and record whether the interaction succeeded
- skip obviously destructive controls instead of performing them
- write a machine-readable JSON report

## Install

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
```

## Run

```bash
python crawler.py --url http://localhost:3000 --same-origin-only
```

Optional:

```bash
python crawler.py \
  --url http://localhost:3000 \
  --same-origin-only \
  --max-pages 200 \
  --timeout 20000 \
  --out crawl-report.json
```

## Important limitation

A click succeeding at the browser level does **not** prove the product action is correct.

The crawler is the first layer. For critical buttons, add explicit assertions such as:

- expected URL/state change
- expected API response
- expected database-side effect
- expected UI state
- expected error state

That turns the crawler from a smoke test into a real end-to-end regression suite.

## Safety

Destructive-looking controls are skipped by default. Do not remove that protection until the test environment and action-specific assertions are in place.
