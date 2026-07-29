from pathlib import Path

import pytest

from cvb.scenarios import CATEGORIES, load_scenarios, validate_scenario

GOOD = {
    "id": "no-requests-lib",
    "category": "library-choice",
    "task": "Write a fetch function.",
    "constraints": [
        {"id": "c1", "text": "use httpx, never requests", "why": "proxy incident", "checks": [
            {"type": "regex_absent", "pattern": r"\brequests\b", "description": "uses requests"}]},
        {"id": "c2", "text": "network calls carry a timeout", "why": "hung deploy", "checks": [
            {"type": "regex_present", "pattern": r"timeout", "description": "no timeout"}]},
    ],
}


def test_valid_scenario_passes():
    assert validate_scenario(GOOD) == []


def test_bad_category_flagged():
    s = dict(GOOD, category="nope")
    assert any("category" in p for p in validate_scenario(s))


def test_single_constraint_flagged():
    s = dict(GOOD, constraints=GOOD["constraints"][:1])
    assert any("2-4" in p for p in validate_scenario(s))


def test_imperative_wording_flagged():
    bad = dict(GOOD)
    bad["constraints"] = [dict(GOOD["constraints"][0]), dict(GOOD["constraints"][1])]
    bad["constraints"][0] = dict(bad["constraints"][0], text="you must use httpx")
    assert any("imperative" in p for p in validate_scenario(bad))


def test_bad_regex_flagged():
    bad = dict(GOOD)
    bad["constraints"] = [dict(GOOD["constraints"][0], checks=[
        {"type": "regex_absent", "pattern": "(", "description": "broken"}]), GOOD["constraints"][1]]
    assert any("regex" in p for p in validate_scenario(bad))


def test_all_committed_scenarios_valid_and_quota_met():
    scenarios = load_scenarios(Path(__file__).parent.parent / "scenarios")
    assert len(scenarios) >= 35
    per_cat = {c: 0 for c in CATEGORIES}
    for s in scenarios:
        per_cat[s["category"]] += 1
    assert all(n >= 5 for n in per_cat.values()), per_cat
