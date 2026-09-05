"""The operator screen, driven in a real browser.

Real Chromium, real page, real clicks, against the same real server the
API tests use. The point of these tests is the behaviour you cannot see
from the API alone: that the screen shows the customer exactly what they
are approving before anything happens, and that nothing is written until
they click Approve.
"""

import sys
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from hands import api, documents, shelf, store  # noqa: E402

sync_playwright = pytest.importorskip(
    "playwright.sync_api", reason="Playwright is required for the browser tests").sync_playwright

TOKEN = "test-token-not-a-secret"

FORM_SPEC = [
    {"name": "worker_name", "label": "Worker name", "value": "", "rect": [150, 700, 400, 715]},
    {"name": "site_address", "label": "Site address", "value": "12 Rundle St, Adelaide",
     "rect": [150, 660, 400, 675]},
    {"name": "induction_complete_declaration", "label": "Induction declaration", "value": "",
     "rect": [150, 620, 400, 635]},
]


@pytest.fixture
def server(tmp_path):
    root = tmp_path / "hands-data"
    httpd, _ = api.serve(host="127.0.0.1", port=0, data_root=str(root), token=TOKEN)
    yield f"http://{httpd.server_address[0]}:{httpd.server_address[1]}", str(root)
    httpd.shutdown()
    httpd.server_close()


@pytest.fixture
def pdf_path(tmp_path):
    path = tmp_path / "site-induction.pdf"
    shelf.pdf_form_filling.render_pdf_with_form(str(path), "Site induction", FORM_SPEC)
    return path


@pytest.fixture
def page():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context()
        yield context.new_page()
        context.close()
        browser.close()


def open_session(page, base_url, pdf_path):
    page.goto(base_url)
    page.fill('[data-testid="token"]', TOKEN)
    page.dispatch_event('[data-testid="token"]', "change")
    page.wait_for_function("document.querySelectorAll('[data-testid=workflow] option').length > 0")
    page.select_option('[data-testid="workflow"]', "document_completion")
    page.click('[data-testid="start"]')
    page.wait_for_selector('[data-testid="panel-document"]:not([hidden])')
    page.set_input_files('[data-testid="file"]', str(pdf_path))
    page.click('[data-testid="upload"]')
    page.wait_for_selector('[data-testid="prov-worker_name"]')


def test_the_screen_shows_real_field_state_from_the_real_document(server, page, pdf_path):
    base_url, _ = server
    open_session(page, base_url, pdf_path)

    assert page.inner_text('[data-testid="prov-site_address"]') == "KNOWN"
    assert page.inner_text('[data-testid="value-site_address"]') == "12 Rundle St, Adelaide"
    assert page.inner_text('[data-testid="prov-worker_name"]') == "MISSING"
    assert page.inner_text('[data-testid="state"]') == "WAITING_FOR_INFORMATION"


def test_nothing_is_written_until_the_customer_clicks_approve(server, page, pdf_path):
    base_url, root = server
    open_session(page, base_url, pdf_path)

    page.click('[data-testid="lock-price"]')
    page.fill('[data-testid="supply-worker_name"]', "Sam Naylor")
    page.dispatch_event('[data-testid="supply-worker_name"]', "change")
    page.wait_for_selector('[data-testid="value-worker_name"]')
    page.fill('[data-testid="supply-induction_complete_declaration"]',
              "I have completed the site induction")
    page.dispatch_event('[data-testid="supply-induction_complete_declaration"]', "change")
    page.wait_for_function(
        "document.querySelector('[data-testid=state]').textContent === 'READY'")

    page.click('[data-testid="execute"]')
    page.wait_for_selector('[data-testid="panel-gate"]:not([hidden])')

    shown = page.inner_text('[data-testid="gate-payload"]')
    assert "induction_complete_declaration" in shown
    assert "Sam Naylor" in shown, "the customer must see the actual values before approving them"
    assert page.inner_text('[data-testid="state"]') == "ACTION_REQUIRED"

    conn = store.connect(root)
    try:
        session_id = page.inner_text('[data-testid="session-id"]')
        assert documents.documents_for(conn, session_id, role="completed") == [], \
            "the gate is open on screen, so nothing may exist on disk yet"
    finally:
        conn.close()

    page.click('[data-testid="approve"]')
    page.wait_for_selector('[data-testid="doc-completed"]')

    page.click('[data-testid="finalise"]')
    page.wait_for_selector('[data-testid="panel-gate"]:not([hidden])')
    page.click('[data-testid="approve"]')
    page.wait_for_function(
        "document.querySelector('[data-testid=state]').textContent === 'COMPLETED'")

    assert "attested" in page.inner_text('[data-testid="doc-completed"]')
    conn = store.connect(root)
    try:
        session_id = page.inner_text('[data-testid="session-id"]')
        completed = documents.documents_for(conn, session_id, role="completed")
        assert len(completed) == 1
        assert documents.attestation_valid(conn, completed[0]["id"]) is True
        assert documents.original_intact(conn, session_id) is True
    finally:
        conn.close()


def test_declining_in_the_browser_ends_the_session_declined(server, page, pdf_path):
    base_url, root = server
    open_session(page, base_url, pdf_path)
    page.click('[data-testid="lock-price"]')
    for field, value in (("worker_name", "Sam Naylor"),
                         ("induction_complete_declaration", "I have completed the site induction")):
        page.fill(f'[data-testid="supply-{field}"]', value)
        page.dispatch_event(f'[data-testid="supply-{field}"]', "change")
        page.wait_for_selector(f'[data-testid="value-{field}"]')

    page.click('[data-testid="execute"]')
    page.wait_for_selector('[data-testid="panel-gate"]:not([hidden])')
    page.click('[data-testid="decline"]')
    page.wait_for_function(
        "document.querySelector('[data-testid=state]').textContent === 'DECLINED'")

    conn = store.connect(root)
    try:
        session_id = page.inner_text('[data-testid="session-id"]')
        assert documents.documents_for(conn, session_id, role="completed") == []
    finally:
        conn.close()


def test_the_screen_refuses_to_work_without_a_token(server, page):
    base_url, _ = server
    page.goto(base_url)
    page.wait_for_selector('[data-testid="error"]:not([hidden])')
    assert "401" in page.inner_text('[data-testid="error"]')
