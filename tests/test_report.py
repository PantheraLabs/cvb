# tests/test_report.py
from cvb.report import aggregate, to_markdown

RESULT = {"prompt_version": "2.0", "runs_per_arm": 1, "records": [
    {"model": "m1", "scenario_id": "s1", "category": "security", "arm": "mandated", "run": 0,
     "constraints": [{"constraint_id": "c1", "violated": False, "failed_checks": []},
                     {"constraint_id": "c2", "violated": False, "failed_checks": []}]},
    {"model": "m1", "scenario_id": "s1", "category": "security", "arm": "incentivized", "run": 0,
     "constraints": [{"constraint_id": "c1", "violated": True, "failed_checks": ["x"]},
                     {"constraint_id": "c2", "violated": False, "failed_checks": []}]},
    {"model": "m1", "scenario_id": "s1", "category": "security", "arm": "cold", "run": 0,
     "constraints": [{"constraint_id": "c1", "violated": True, "failed_checks": ["x"]},
                     {"constraint_id": "c2", "violated": True, "failed_checks": ["y"]}]},
]}


def test_aggregate_strict_and_constraint_accuracy():
    agg = aggregate(RESULT)
    m1 = agg["models"]["m1"]
    assert m1["arms"]["mandated"]["strict_accuracy"] == 1.0
    assert m1["arms"]["incentivized"]["strict_accuracy"] == 0.0
    assert m1["arms"]["incentivized"]["constraint_accuracy"] == 0.5
    assert m1["arms"]["cold"]["constraint_accuracy"] == 0.0
    assert m1["gap"] == 1.0  # mandated 1.0 - incentivized 0.0


def test_markdown_contains_gap_table():
    md = to_markdown(aggregate(RESULT))
    assert "| m1 |" in md and "gap" in md.lower()
