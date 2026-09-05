"""The 15 interfaces, in a real browser: one family per design here (the
full 5x3 run plus the file-opened demo runs is packages/interfaces/
drive_interfaces.py, whose evidence ships with the interfaces). Every
control is pressed and every outcome re-read from the API."""
import asyncio
import os
import sys
from pathlib import Path

import pytest
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
IFACE = ROOT / "packages" / "interfaces"
sys.path.insert(0, str(IFACE))
import build_families as bf      # noqa: E402
import make_interfaces as mi     # noqa: E402
import drive_interfaces as di    # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def built():
    for family in bf.FAMILIES:
        bf.build_family(family)
        mi.make(family)
    os.makedirs(di.SHOTS, exist_ok=True)


@pytest.mark.parametrize("family,design", [("pm-teamwork", "console"), ("erp-backbone", "board"), ("accounting-ledger", "pocket")])
def test_every_control_works_and_is_verified_by_the_api(family, design):
    async def go():
        async with async_playwright() as pw:
            with di.Server(family, bf.PORTS[family] + 200) as srv:
                return await di.drive_one(pw, family, design, srv.port)
    r = asyncio.run(go())
    assert r["failed"] == [], r["failed"]
    assert r["browser_errors"] == []
    assert r["passed"] >= 30


def test_opened_as_a_file_the_interface_still_works_on_its_demo_store():
    async def go():
        async with async_playwright() as pw:
            return await di.drive_one(pw, "crm-pipeline", "board", None)
    r = asyncio.run(go())
    assert r["failed"] == [], r["failed"]
    assert r["mode"] == "file"
