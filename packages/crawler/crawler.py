#!/usr/bin/env python3
"""
Universal browser crawler / smoke-test harness.

Requires:
    pip install playwright
    playwright install chromium

Usage:
    python crawler.py --url http://localhost:3000
    python crawler.py --url http://localhost:3000 --max-pages 100
    python crawler.py --url http://localhost:3000 --same-origin-only
"""

import argparse, asyncio, json, re, time
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError


SKIP_SCHEMES = ("mailto:", "tel:", "javascript:", "data:")
SKIP_EXTENSIONS = re.compile(
    r"\.(?:png|jpe?g|gif|webp|svg|ico|pdf|zip|gz|mp4|mp3|wav|woff2?|ttf|css|js)$",
    re.I,
)


def normalize(url):
    url, _ = urldefrag(url)
    return url.rstrip("/") or url


def usable_link(href):
    if not href or href.startswith(SKIP_SCHEMES):
        return False
    return not SKIP_EXTENSIONS.search(urlparse(href).path)


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--max-pages", type=int, default=100)
    ap.add_argument("--timeout", type=int, default=15000)
    ap.add_argument("--same-origin-only", action="store_true")
    ap.add_argument("--out", default="crawl-report.json")
    args = ap.parse_args()

    start = normalize(args.url)
    origin = urlparse(start).netloc
    queue = [start]
    seen = set()
    results = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page()

        console_errors = []
        page_errors = []
        failed_requests = []

        page.on("console", lambda msg:
                console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))
        page.on("requestfailed", lambda req:
                failed_requests.append({"url": req.url, "error": req.failure}))

        while queue and len(seen) < args.max_pages:
            url = queue.pop(0)
            if url in seen:
                continue
            seen.add(url)

            item = {
                "url": url,
                "status": "unknown",
                "title": "",
                "links": 0,
                "buttons": 0,
                "button_results": [],
                "console_errors": [],
                "page_errors": [],
                "failed_requests": [],
                "duration_ms": 0,
            }

            started = time.perf_counter()
            try:
                response = await page.goto(
                    url, wait_until="domcontentloaded", timeout=args.timeout
                )
                item["status"] = response.status if response else None
                item["title"] = await page.title()

                # Discover navigation targets.
                hrefs = await page.locator("a[href]").evaluate_all(
                    "(els) => els.map(e => e.href)"
                )
                for href in hrefs:
                    href = normalize(href)
                    if not usable_link(href):
                        continue
                    parsed = urlparse(href)
                    if args.same_origin_only and parsed.netloc != origin:
                        continue
                    if parsed.scheme not in ("http", "https"):
                        continue
                    if href not in seen and href not in queue:
                        queue.append(href)

                # Exercise visible buttons. This is intentionally conservative:
                # clicks are attempted, but destructive-looking controls are skipped.
                buttons = page.locator("button:visible, input[type=button]:visible, input[type=submit]:visible")
                count = await buttons.count()
                item["buttons"] = count

                for i in range(count):
                    b = buttons.nth(i)
                    label = (
                        await b.get_attribute("aria-label")
                        or await b.inner_text()
                        or await b.get_attribute("value")
                        or ""
                    ).strip()

                    lower = label.lower()
                    if any(word in lower for word in (
                        "delete", "remove", "destroy", "logout", "sign out",
                        "purchase", "pay", "charge", "submit order"
                    )):
                        item["button_results"].append({
                            "label": label,
                            "result": "skipped-destructive",
                        })
                        continue

                    before_url = page.url
                    try:
                        await b.click(timeout=args.timeout)
                        await page.wait_for_timeout(300)
                        item["button_results"].append({
                            "label": label,
                            "result": "clicked",
                            "url_after": page.url,
                            "navigation_changed": page.url != before_url,
                        })
                    except Exception as exc:
                        item["button_results"].append({
                            "label": label,
                            "result": "failed",
                            "error": str(exc),
                        })

            except PlaywrightTimeoutError as exc:
                item["status"] = "timeout"
                item["error"] = str(exc)
            except Exception as exc:
                item["status"] = "error"
                item["error"] = str(exc)

            item["duration_ms"] = round((time.perf_counter() - started) * 1000)
            item["console_errors"] = console_errors[:]
            item["page_errors"] = page_errors[:]
            item["failed_requests"] = failed_requests[:]
            console_errors.clear()
            page_errors.clear()
            failed_requests.clear()
            results.append(item)

        await browser.close()

    report = {
        "start_url": start,
        "pages_scanned": len(results),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "pages": results,
    }

    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Scanned {len(results)} pages.")
    print(f"Report: {args.out}")


if __name__ == "__main__":
    asyncio.run(main())
