"""Scenario loading and lint. Every scenario file must pass validate_scenario
before it can ship — the lint enforces the schema AND the imperative-free
wording that keeps the incentivized arm honest."""
from __future__ import annotations

import json
import re
from pathlib import Path

CATEGORIES = (
    "library-choice",
    "security",
    "encoding-io",
    "style-architecture",
    "error-handling",
    "concurrency",
    "logging-testing",
)

_KEBAB_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_BANNED_WORDS = ("must", "you should", "required", "rule")
_CHECK_TYPES = ("regex_absent", "regex_present", "regex_absent_unless")


def validate_scenario(s: dict) -> list[str]:
    problems: list[str] = []

    sid = s.get("id")
    if not isinstance(sid, str) or not _KEBAB_RE.match(sid or ""):
        problems.append(f"id missing or not kebab-case: {sid!r}")
    if s.get("category") not in CATEGORIES:
        problems.append(f"bad category: {s.get('category')!r}")
    if not isinstance(s.get("task"), str) or not s.get("task", "").strip():
        problems.append("task missing or empty")

    constraints = s.get("constraints")
    if not isinstance(constraints, list) or not (2 <= len(constraints) <= 4):
        problems.append("constraints must be 2-4")
        constraints = constraints if isinstance(constraints, list) else []

    seen_cids: set[str] = set()
    for c in constraints:
        cid = c.get("id", "<missing>")
        if cid in seen_cids:
            problems.append(f"duplicate constraint id: {cid}")
        seen_cids.add(cid)
        for key in ("id", "text", "why"):
            if not isinstance(c.get(key), str) or not c.get(key, "").strip():
                problems.append(f"constraint {cid}: {key} missing or empty")
        wording = (str(c.get("text", "")) + " " + str(c.get("why", ""))).lower()
        for banned in _BANNED_WORDS:
            if banned in wording:
                problems.append(f"constraint {cid}: imperative wording ({banned!r})")
        checks = c.get("checks")
        if not isinstance(checks, list) or len(checks) < 1:
            problems.append(f"constraint {cid}: needs >= 1 check")
            continue
        for chk in checks:
            if chk.get("type") not in _CHECK_TYPES:
                problems.append(f"constraint {cid}: unknown check type {chk.get('type')!r}")
                continue
            if not isinstance(chk.get("description"), str) or not chk.get("description", "").strip():
                problems.append(f"constraint {cid}: check missing description")
            try:
                re.compile(chk.get("pattern", ""))
            except re.error as exc:
                problems.append(f"constraint {cid}: bad regex ({exc})")
            if chk.get("type") == "regex_absent_unless" and not chk.get("unless"):
                problems.append(f"constraint {cid}: regex_absent_unless needs 'unless'")

    return problems


def load_scenarios(dir_path: str | Path) -> list[dict]:
    dir_path = Path(dir_path)
    scenarios: list[dict] = []
    seen_ids: set[str] = set()
    errors: list[str] = []
    for path in sorted(dir_path.glob("*.json")):
        with open(path, encoding="utf-8") as fh:
            scenario = json.load(fh)
        problems = validate_scenario(scenario)
        if problems:
            errors.append(f"{path.name}: " + "; ".join(problems))
            continue
        if scenario["id"] in seen_ids:
            errors.append(f"{path.name}: duplicate scenario id {scenario['id']}")
            continue
        seen_ids.add(scenario["id"])
        scenarios.append(scenario)
    if errors:
        raise ValueError("invalid scenarios:\n" + "\n".join(errors))
    return sorted(scenarios, key=lambda s: s["id"])
