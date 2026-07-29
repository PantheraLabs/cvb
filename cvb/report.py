"""Aggregate runner results into per-model accuracy metrics and markdown tables.

Consumes the result JSON produced by ``cvb.runner`` (see its record shape) and
produces:

- ``strict_accuracy``: fraction of runs where ZERO constraints were violated.
- ``constraint_accuracy``: fraction of constraint evaluations not violated.
- ``gap``: mandated strict_accuracy minus incentivized strict_accuracy.

Stdlib only; plain dict math, no pandas.
"""
from __future__ import annotations

import argparse
import json

_ARM_ORDER = ("cold", "mandated", "incentivized")


def _accuracies(records: list[dict]) -> dict:
    """Strict + constraint accuracy over a list of run records."""
    strict_hits = 0
    constraint_total = 0
    constraint_ok = 0
    for rec in records:
        constraints = rec["constraints"]
        if not any(c["violated"] for c in constraints):
            strict_hits += 1
        constraint_total += len(constraints)
        constraint_ok += sum(1 for c in constraints if not c["violated"])
    n = len(records)
    return {
        "strict_accuracy": strict_hits / n if n else 0.0,
        "constraint_accuracy": constraint_ok / constraint_total if constraint_total else 0.0,
    }


def aggregate(result: dict) -> dict:
    """Aggregate a runner result dict into per-model / per-arm metrics."""
    by_model: dict[str, list[dict]] = {}
    for rec in result["records"]:
        by_model.setdefault(rec["model"], []).append(rec)

    models: dict[str, dict] = {}
    for model, recs in sorted(by_model.items()):
        arms: dict[str, dict] = {}
        categories: dict[str, dict] = {}
        by_arm: dict[str, list[dict]] = {}
        by_cat_arm: dict[str, dict[str, list[dict]]] = {}
        for rec in recs:
            by_arm.setdefault(rec["arm"], []).append(rec)
            by_cat_arm.setdefault(rec["category"], {}).setdefault(rec["arm"], []).append(rec)
        for arm, arm_recs in by_arm.items():
            arms[arm] = _accuracies(arm_recs)
        for cat, cat_arms in sorted(by_cat_arm.items()):
            categories[cat] = {arm: _accuracies(r) for arm, r in cat_arms.items()}
        mandated = arms.get("mandated", {}).get("strict_accuracy", 0.0)
        incentivized = arms.get("incentivized", {}).get("strict_accuracy", 0.0)
        models[model] = {
            "arms": arms,
            "gap": mandated - incentivized,
            "categories": categories,
        }
    return {"models": models}


def _fmt(value: float | None) -> str:
    return "-" if value is None else f"{value:.3f}"


def _arm_strict(arms: dict, arm: str) -> float | None:
    if arm in arms:
        return arms[arm]["strict_accuracy"]
    return None


def to_markdown(agg: dict) -> str:
    """Render aggregated metrics as ASCII markdown tables."""
    lines: list[str] = []
    lines.append("# CVB Report")
    lines.append("")
    lines.append("## Headline: strict accuracy by arm")
    lines.append("")
    lines.append("| model | cold | mandated | incentivized | gap (mandated - incentivized) |")
    lines.append("| --- | --- | --- | --- | --- |")
    for model, data in agg["models"].items():
        arms = data["arms"]
        lines.append(
            "| {model} | {cold} | {mandated} | {incentivized} | {gap} |".format(
                model=model,
                cold=_fmt(_arm_strict(arms, "cold")),
                mandated=_fmt(_arm_strict(arms, "mandated")),
                incentivized=_fmt(_arm_strict(arms, "incentivized")),
                gap=_fmt(data["gap"]),
            )
        )
    lines.append("")
    for model, data in agg["models"].items():
        lines.append(f"## {model} by category (strict accuracy)")
        lines.append("")
        lines.append("| category | cold | mandated | incentivized |")
        lines.append("| --- | --- | --- | --- |")
        for cat, cat_arms in data["categories"].items():
            cells = [
                _fmt(cat_arms[arm]["strict_accuracy"]) if arm in cat_arms else "-"
                for arm in _ARM_ORDER
            ]
            lines.append(f"| {cat} | {cells[0]} | {cells[1]} | {cells[2]} |")
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m cvb.report",
        description="Aggregate a CVB result JSON into markdown tables.",
    )
    parser.add_argument("result_json", help="path to runner output JSON (e.g. results/out.json)")
    parser.add_argument("--markdown", help="write markdown report to this path instead of stdout")
    args = parser.parse_args(argv)

    with open(args.result_json, encoding="utf-8") as f:
        result = json.load(f)
    md = to_markdown(aggregate(result))
    if args.markdown:
        with open(args.markdown, "w", encoding="utf-8") as f:
            f.write(md + "\n")
        print(f"wrote {args.markdown}")
    else:
        print(md)


if __name__ == "__main__":
    main()
