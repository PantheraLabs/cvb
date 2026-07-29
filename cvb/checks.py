"""Deterministic violation checks. No LLM judge: a pass means "no detected
violation", not proof of compliance."""
from __future__ import annotations

import re

_FENCE_RE = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)


def extract_code(text: str) -> str:
    blocks = _FENCE_RE.findall(text)
    if blocks:
        return "\n".join(b.strip("\n") for b in blocks)
    return text


def evaluate_check(check: dict, code: str) -> bool:
    pattern = re.compile(check["pattern"], re.MULTILINE)
    kind = check["type"]
    if kind == "regex_absent":
        return pattern.search(code) is not None
    if kind == "regex_present":
        return pattern.search(code) is None
    if kind == "regex_absent_unless":
        unless = check["unless"]
        return any(unless not in m.group(0) for m in pattern.finditer(code))
    raise ValueError(f"unknown check type: {kind}")


def evaluate_constraint(constraint: dict, code: str) -> dict:
    failed = [c["description"] for c in constraint["checks"] if evaluate_check(c, code)]
    return {
        "constraint_id": constraint["id"],
        "violated": bool(failed),
        "failed_checks": failed,
    }
