"""Every rule must fire on a spec built to violate it, and the good spec must pass clean."""
import copy
import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import specgate  # noqa: E402
import decompose  # noqa: E402

GOOD = yaml.safe_load(open(pathlib.Path(__file__).resolve().parents[1] / "examples" / "good.spec.yaml", encoding="utf-8"))


def rules(spec):
    failures, _ = specgate.check(spec)
    return {f["rule"] for f in failures}, failures


def test_good_spec_passes_clean():
    fired, failures = rules(GOOD)
    assert fired == set(), failures


def test_good_spec_counts_human_criteria_separately():
    _, summary = specgate.check(GOOD)
    assert summary["criteria_machine"] == 3
    assert summary["criteria_human"] == 1


def mut():
    return copy.deepcopy(GOOD)


def test_R1_missing_field():
    s = mut(); del s["intent"]["goal"]
    assert "R1" in rules(s)[0]
    s = mut(); s["substance"]["externals"] = []
    assert "R1" in rules(s)[0]


def test_R1_declared_absence_is_accepted():
    s = mut()
    s["substance"]["externals"] = {"none": "fully offline, no outside services"}
    fired, failures = rules(s)
    assert "R1" not in fired, failures
    # R6 must not fire on a declared absence either
    assert "R6" not in fired


def test_R2_ask_marker_and_exit_semantics():
    s = mut(); s["intent"]["goal"] += " [ASK: which Google account?]"
    fired, _ = rules(s)
    assert fired == {"R2"}  # R2-only → ask-ready path


def test_R3_missing_verify():
    s = mut(); del s["gate"]["acceptance"][0]["verify"]
    assert "R3" in rules(s)[0]
    s = mut(); s["gate"]["acceptance"] = []
    assert "R3" in rules(s)[0]


def test_R3_human_criterion_needs_no_verify():
    fired, _ = rules(GOOD)  # AC-04 has no verify and human: true
    assert "R3" not in fired


def test_R4_banned_words_with_word_boundaries():
    s = mut(); s["gate"]["acceptance"][0]["check"] = "The connect button works"
    assert "R4" in rules(s)[0]
    s = mut(); s["gate"]["acceptance"][0]["check"] = "Errors are handled gracefully by the tile"
    assert "R4" in rules(s)[0]
    # 'networks' must NOT trip 'works'; 'cleanup' must not trip 'clean'
    s = mut(); s["gate"]["acceptance"][0]["check"] = "Reconnects across networks after cleanup and the response is 302"
    fired, failures = rules(s)
    assert "R4" not in fired, failures


def test_R5_control_without_endpoint_or_display_only():
    s = mut(); del s["substance"]["surfaces"][0]["controls"][0]["endpoint"]
    assert "R5" in rules(s)[0]
    s = mut(); del s["substance"]["surfaces"][0]["controls"][1]["source"]
    assert "R5" in rules(s)[0]


def test_R6_external_without_custodian():
    s = mut(); del s["substance"]["externals"][0]["custodian"]
    assert "R6" in rules(s)[0]


def test_R7_missing_policy():
    s = mut(); del s["gate"]["missing_info_policy"]
    assert "R7" in rules(s)[0]


def test_R8_eight_constraints():
    s = mut(); s["bounds"]["constraints"] = [f"c{i}" for i in range(8)]
    assert "R8" in rules(s)[0]


def test_R9_empty_out_of_scope():
    s = mut(); s["intent"]["out_of_scope"] = []
    fired, _ = rules(s)
    assert "R9" in fired or "R1" in fired  # empty list is both absent (R1) and never-true (R9)


def test_R10_self_report_verify():
    s = mut(); s["gate"]["acceptance"][0]["verify"] = "builder confirms the tests pass"
    assert "R10" in rules(s)[0]


def test_R11_irreversible_action_without_rollback():
    s = mut(); del s["substance"]["actions"][1]["rollback"]
    assert "R11" in rules(s)[0]
    s = mut(); del s["substance"]["actions"][0]["reversible"]
    assert "R11" in rules(s)[0]


def test_R12_data_without_location():
    s = mut(); del s["substance"]["data"][0]["location"]
    assert "R12" in rules(s)[0]


# ---------------- decomposition ----------------

def test_decompose_good(tmp_path):
    errors, plan = decompose.decompose(GOOD, tmp_path)
    assert errors == []
    assert plan["waves"] == [["SPEC-014/P1"], ["SPEC-014/P2"]]
    files = list((tmp_path / "SPEC-014").glob("*.yaml"))
    assert len(files) == 2
    p1 = yaml.safe_load(open(tmp_path / "SPEC-014" / "SPEC-014_P1.yaml", encoding="utf-8"))
    assert p1["attempt"] == 1 and len(p1["idempotency_key"]) == 16
    assert p1["missing_info"].startswith("Stop and ask")


def test_D1_unapproved(tmp_path):
    s = mut(); s["header"]["status"] = "draft"
    errors, _ = decompose.decompose(s, tmp_path)
    assert any(e["rule"] == "D1" for e in errors)


def test_D4_cross_packet_reference(tmp_path):
    s = mut()
    s["packets"][1]["inputs"]["table_ddl"] = "see packet SPEC-014/P1 output"
    errors, _ = decompose.decompose(s, tmp_path)
    assert any(e["rule"] == "D4" for e in errors)


def test_D5_uncovered_and_double_covered(tmp_path):
    s = mut(); s["packets"][1]["acceptance"] = []
    errors, _ = decompose.decompose(s, tmp_path)
    assert any(e["rule"] == "D5" for e in errors)  # AC-03 uncovered, and D3 empty field
    s = mut(); s["packets"][1]["acceptance"] = ["AC-01", "AC-03"]
    errors, _ = decompose.decompose(s, tmp_path)
    assert any(e["rule"] == "D5" and "AC-01" in e["message"] for e in errors)


def test_D7_cycle(tmp_path):
    s = mut()
    s["packets"][0]["depends_on"] = ["SPEC-014/P2"]
    errors, _ = decompose.decompose(s, tmp_path)
    assert any(e["rule"] == "D7" for e in errors)


def test_D8_budget_overrun(tmp_path):
    s = mut(); s["packets"][0]["budget"] = 30; s["packets"][1]["budget"] = 20
    errors, _ = decompose.decompose(s, tmp_path)
    assert any(e["rule"] == "D8" for e in errors)
