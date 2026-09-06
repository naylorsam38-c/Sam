"""The front door: eight answers -> a real, checked, built app.

The browser proof (a person answering the questions, and the app they are
handed being used) is packages/frontdoor/prove_frontdoor.py, whose evidence
ships with it. These are the fast checks that guard the rules underneath it."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FD = ROOT / "packages" / "frontdoor"
sys.path.insert(0, str(FD))
import catalogue as cat   # noqa: E402
import intake             # noqa: E402
import matcher            # noqa: E402


def test_the_catalogue_only_promises_what_a_template_really_declares():
    """The whole front door rests on this: a card the person can tap must name
    only pieces that really exist, or the build would refuse after they chose."""
    assert cat.verify() is cat.CAPABILITIES


def test_a_card_that_promises_a_record_no_template_has_is_refused():
    bad = json.loads(json.dumps(cat.CAPABILITIES))
    bad[0]["records"].append("Unicorn")
    with pytest.raises(cat.CatalogueError) as e:
        cat.verify(bad)
    assert "Unicorn" in str(e.value)


def test_every_unavailable_thing_says_why_and_what_instead():
    for g in cat.NOT_ON_THE_SHELF:
        assert g["plain"] and g["why"], g
        assert "instead" in g, g


def test_their_own_words_find_the_right_card_and_name_the_impossible_ask():
    hits, gaps = cat.match("connecting people, keep their details, and let them chat to each other")
    assert "people" in [h["id"] for h in hits]
    assert "messaging" in [g["id"] for g in gaps], "asking for chat must be caught before they choose"


def test_open_items_are_four_and_the_boss_tie_break_only_when_two_supers_appear():
    """Design 3 replaced the eight-question flow's own boss logic with
    matcher.match()'s open_items: still no default for who/density/mark/
    must_not, and the boss tie-break only appears when the matched cards
    bring two different people-in-charge."""
    p1 = matcher.match(intake.EXAMPLES["connecting-people"]["does"])
    assert [o["id"] for o in p1.open_items] == ["who", "density", "mark", "must_not"]
    p2 = matcher.match(intake.EXAMPLES["clinic"]["does"])
    assert [o["id"] for o in p2.open_items] == ["who", "boss", "density", "mark", "must_not"]


def test_nothing_picked_is_refused_not_guessed_at():
    with pytest.raises(intake.IntakeRefused):
        intake.build_instance({"cards": [], "who": "just_me", "look": "board",
                               "density": "balanced", "mark": "orbit", "name": "X", "does": "y"})


def test_two_families_with_two_bosses_refuse_until_the_person_says_who_is_in_charge():
    answers = {"does": "bookings and invoices", "cards": ["bookings", "money"], "who": "small_team",
               "look": "board", "density": "balanced", "mark": "wave", "name": "Clinic", "must_not": "nothing"}
    with pytest.raises(intake.IntakeRefused) as e:
        intake.build_instance(answers)
    assert "in charge" in str(e.value)
    answers["boss"] = "Owner"
    inst, filled = intake.build_instance(answers)
    assert inst["super_role"] == "Owner"
    assert inst["per_instance"]["P.01:Admin"], "the demoted role must be given real authority answers"
    assert any("authority of Admin" in what for what, _ in filled), "and the person must be told"


@pytest.mark.parametrize("example", sorted(intake.EXAMPLES))
def test_each_worked_example_builds_a_real_app(example, tmp_path):
    answers = intake.EXAMPLES[example]
    spec, app_dir, result, filled = intake.run(answers, str(tmp_path / example), port=0)
    assert (Path(app_dir) / "app.py").exists()
    assert (Path(app_dir) / "static" / "ui-console.html").exists()
    assert (Path(app_dir) / "static" / "ui-board.html").exists()
    assert (Path(app_dir) / "static" / "ui-pocket.html").exists()
    assert result["screens_built"] > 0 and result["records_built"]
    summary = (Path(app_dir).parent / "YOUR_APP.md").read_text()
    assert "What this does NOT do" in summary, "the summary must always say what was not built"
    assert answers["name"] in summary


def test_every_answer_filled_in_without_asking_carries_its_reason():
    inst, filled = intake.build_instance(intake.EXAMPLES["connecting-people"])
    assert filled, "there are unasked questions, so they must be listed"
    for what, why in filled:
        assert what and why and len(why) > 20, (what, why)
    assert inst["ask_customer"] == [], "nothing may be left open once the front door is done"
