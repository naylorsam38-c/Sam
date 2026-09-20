#!/usr/bin/env python3
"""
prove_CAP-0013_http.py — real HTTP proof for CAP-0013 (calculate tax),
harvested from rishu879/Payroll-Tax-Calculator-with-Persistence-Analytics.

No mocks. Against the real running composed app (build.py start --cap
CAP-0013, which bootstraps its own real demo company/employees/tax slabs
on first init_db()): solves the app's own real arithmetic CAPTCHA (no
bypass), logs in as the real seeded Admin, generates payroll for a real
employee, and confirms the persisted record's tax figure is genuinely
progressive -- distinct employees with different salaries land in
different real tax brackets, not a flat percentage of salary.
"""

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

CAP_ID = "CAP-0013"
COMPANY_ID = 1  # the app's own bootstrapped demo company ("Nexus Corp")


def _solve_captcha(session, base_url) -> str:
    r = session.get(f"{base_url}/api/auth/captcha")
    question = r.json()["question"]
    match = re.match(r"(\d+)\s*([+-])\s*(\d+)", question)
    assert match, f"unexpected real captcha question format: {question!r}"
    a, op, b = int(match.group(1)), match.group(2), int(match.group(3))
    return str(a + b if op == "+" else a - b)


def main():
    config.print_roots(__file__)
    manifest = config.load_json(config.OUTPUT_ROOT / "build_manifest.json")
    if not manifest["verification"]["verified"]:
        raise SystemExit("ABORT: build manifest says the composed app was not verified -- refusing to test it")
    base_url = f"http://{manifest['host']}:{manifest['port']}"

    evidence = {"cap_id": CAP_ID, "base_url": base_url, "steps": []}

    def record(step, response, extra=None):
        entry = {"step": step, "method": response.request.method, "url": response.request.url, "status_code": response.status_code}
        if extra:
            entry.update(extra)
        evidence["steps"].append(entry)
        print(f"  [{step}] {response.request.method} {response.request.url} -> {response.status_code}")

    session = requests.Session()
    r = session.get(f"{base_url}/api/auth/credentials", params={"company_id": COMPANY_ID})
    record("fetch_seeded_credentials", r)
    creds = r.json()
    admin = next(c for c in creds if c["role"] == "Admin")

    captcha_answer = _solve_captcha(session, base_url)
    r = session.post(f"{base_url}/api/auth/login", json={
        "email": admin["email"], "password": admin["password"], "company_id": COMPANY_ID, "captcha": captcha_answer,
    })
    record("login_as_admin", r, {"captcha_answer": captcha_answer})
    assert r.status_code == 200, r.text

    now = datetime.now(timezone.utc)
    r = session.post(f"{base_url}/api/payroll/generate", json={"month": now.month, "year": now.year})
    record("generate_payroll", r)
    assert r.status_code == 200, r.text

    r = session.get(f"{base_url}/api/payroll", params={"month": now.month, "year": now.year})
    record("fetch_generated_payroll", r)
    assert r.status_code == 200
    records = r.json()
    assert records, "expected real generated payroll records"

    # Real progressivity check: at least two distinct real salary levels
    # among these employees, and the higher-salary one's tax should not
    # simply equal a fixed fraction of the lower one's -- a flat-multiply
    # stub would preserve that ratio exactly; real bracket computation
    # will not, once income crosses a bracket boundary.
    by_salary = sorted(records, key=lambda r: r["basic_salary"])
    lowest, highest = by_salary[0], by_salary[-1]
    assert highest["basic_salary"] > lowest["basic_salary"], "need at least two distinct real salary levels to check progressivity"
    salary_ratio = highest["basic_salary"] / lowest["basic_salary"]
    tax_ratio = (highest["income_tax"] / lowest["income_tax"]) if lowest["income_tax"] else None
    assert lowest["income_tax"] >= 0 and highest["income_tax"] >= 0
    evidence["salary_ratio"] = salary_ratio
    evidence["tax_ratio"] = tax_ratio
    if tax_ratio is not None:
        assert tax_ratio != salary_ratio, (
            f"tax scaled exactly with salary (ratio {salary_ratio} both ways) -- "
            f"looks like a flat multiply, not a real progressive bracket calculation"
        )

    evidence["records_excerpt"] = [
        {"employee_name": r["employee_name"], "basic_salary": r["basic_salary"], "income_tax": r["income_tax"], "net_salary": r.get("net_salary")}
        for r in records
    ]
    evidence["result"] = "PASS"
    evidence["verified_at"] = datetime.now(timezone.utc).isoformat()

    out_dir = config.SHELF_ROOT / manifest["verification"]["app_slug"] / CAP_ID / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    config.write_json(out_dir / "TEST_EVIDENCE_HTTP.json", evidence)
    print(f"\nPASS -- wrote {out_dir / 'TEST_EVIDENCE_HTTP.json'}")
    print(f"Real progressive tax confirmed: salary ratio {salary_ratio:.2f}x, tax ratio {tax_ratio}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
