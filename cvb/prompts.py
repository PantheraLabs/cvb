"""Frozen prompt templates. Changing any wording is a versioned event:
bump PROMPT_VERSION and note it in the README changelog."""
from __future__ import annotations

PROMPT_VERSION = "2.0"
ARMS = ("cold", "mandated", "incentivized")

_PREAMBLE = "You are a senior software engineer. Complete this task:"
_SUFFIX = "Reply with code only."


def build_prompt(arm: str, scenario: dict) -> str:
    task = scenario["task"]
    if arm == "cold":
        return f"{_PREAMBLE}\n\n{task}\n\n{_SUFFIX}"
    if arm == "mandated":
        lines = "\n".join(f"{i + 1}. {c['text']}" for i, c in enumerate(scenario["constraints"]))
        return (
            f"{_PREAMBLE}\n\n"
            "You MUST follow these project rules. Violating any rule is a failure:\n"
            f"{lines}\n\n{task}\n\n{_SUFFIX}"
        )
    if arm == "incentivized":
        lines = "\n".join(
            f"- Recorded decision: {c['text']} (context: {c['why']})"
            for c in scenario["constraints"]
        )
        return (
            f"{_PREAMBLE}\n\n"
            "Project context (from the team's shared memory system):\n"
            f"{lines}\n\n{task}\n\n{_SUFFIX}"
        )
    raise ValueError(f"unknown arm: {arm}")
