import pytest

from cvb.prompts import ARMS, PROMPT_VERSION, build_prompt

SCENARIO = {
    "id": "no-requests-lib",
    "task": "Write a function fetching a JSON document from a URL.",
    "constraints": [
        {"id": "c1", "text": "use httpx, never requests", "why": "requests broke our proxy setup in prod", "checks": []},
        {"id": "c2", "text": "all network calls need a timeout", "why": "hung deploy 2026-03", "checks": []},
    ],
}


def test_arms_tuple():
    assert ARMS == ("cold", "mandated", "incentivized")
    assert PROMPT_VERSION == "2.0"


def test_cold_has_task_but_no_constraints():
    p = build_prompt("cold", SCENARIO)
    assert "fetching a JSON document" in p
    assert "httpx" not in p


def test_mandated_contains_all_constraints_as_orders():
    p = build_prompt("mandated", SCENARIO)
    assert "You MUST follow" in p
    assert "use httpx, never requests" in p
    assert "all network calls need a timeout" in p


def test_incentivized_contains_constraints_without_imperatives():
    p = build_prompt("incentivized", SCENARIO)
    assert "use httpx, never requests" in p
    assert "requests broke our proxy setup in prod" in p  # the why is included
    low = p.lower()
    for banned in ("must", "you should", "required", "rule"):
        assert banned not in low, banned


def test_unknown_arm_raises():
    with pytest.raises(ValueError):
        build_prompt("warm", SCENARIO)
