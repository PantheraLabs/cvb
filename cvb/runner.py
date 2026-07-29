"""Matrix runner: models x scenarios x arms x runs against an
OpenAI-compatible chat completions API. Deterministic settings
(temperature 0), retry with exponential backoff, ASCII-only progress.

CLI:
    python -m cvb.runner --scenarios scenarios --runs 3 --json results/out.json
        [--models a,b] [--base-url URL] [--api-key-env GROQ_API_KEY]
        [--scenario-id ID ...] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx

from cvb.checks import evaluate_constraint, extract_code
from cvb.prompts import ARMS, PROMPT_VERSION, build_prompt
from cvb.scenarios import load_scenarios

DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"
PREFERRED_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "openai/gpt-oss-120b",
    "qwen/qwen3.6-27b",
    "openai/gpt-oss-20b",
]

_MAX_ATTEMPTS = 8
_MAX_BACKOFF = 60.0
# A Retry-After above this is a quota window (daily/TPM), not a transient
# burst limit. Sleeping it out serializes the whole matrix behind one model;
# fail fast instead so run_matrix defers the model and the other models run.
_QUOTA_WALL_RETRY_AFTER = 120.0


def call_model(
    client: httpx.Client,
    base_url: str,
    api_key: str,
    model: str,
    prompt: str,
    backoff_base: float = 1.0,
) -> str:
    """POST a single chat completion. Retries up to _MAX_ATTEMPTS on 429, 5xx,
    or httpx timeout. Sleep between attempts honors the server's Retry-After
    header when present (free-tier rate limits send it), otherwise exponential
    backoff capped at _MAX_BACKOFF. Raises after the final failure."""
    url = f"{base_url}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": 2048,
    }
    last_error: Exception | None = None
    for attempt in range(_MAX_ATTEMPTS):
        retry_after = None
        try:
            response = client.post(url, headers=headers, json=payload)
        except httpx.TimeoutException as exc:
            last_error = exc
        else:
            if response.status_code == 429 or response.status_code >= 500:
                try:
                    retry_after = float(response.headers.get("retry-after", ""))
                except ValueError:
                    retry_after = None
                last_error = httpx.HTTPStatusError(
                    f"retryable status {response.status_code}",
                    request=response.request,
                    response=response,
                )
                if retry_after is not None and retry_after > _QUOTA_WALL_RETRY_AFTER:
                    # Quota window, not a burst limit: retrying is pointless
                    # for minutes/hours. Surface immediately for deferral.
                    raise last_error
            else:
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
        if attempt < _MAX_ATTEMPTS - 1:
            delay = min(backoff_base * 2 ** attempt, _MAX_BACKOFF)
            if retry_after is not None:
                delay = max(retry_after, delay)
            time.sleep(delay)
    assert last_error is not None
    raise last_error


def probe_models(
    client: httpx.Client,
    base_url: str,
    api_key: str,
    preferred: list[str],
) -> list[str]:
    """GET {base_url}/models and return `preferred` filtered to the ids the
    endpoint actually serves, preserving preference order."""
    response = client.get(
        f"{base_url}/models",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    response.raise_for_status()
    available = {entry["id"] for entry in response.json().get("data", [])}
    return [m for m in preferred if m in available]


def run_matrix(
    models: list[str],
    scenarios: list[dict],
    runs: int,
    client: httpx.Client,
    base_url: str,
    api_key: str,
    existing_records: list[dict] | None = None,
    checkpoint_path: str | Path | None = None,
    sleep_between: float = 0.0,
) -> dict:
    """Run every model x scenario x arm x run cell and score each reply.

    Cells already present in existing_records (keyed by model/scenario/arm/run)
    are skipped, which makes crashed runs resumable. When checkpoint_path is
    set, the full result JSON is rewritten after every scenario x arm block so
    a crash never loses more than one block."""
    records: list[dict] = list(existing_records or [])
    done = {(r["model"], r["scenario_id"], r["arm"], r["run"]) for r in records}
    result = {
        "prompt_version": PROMPT_VERSION,
        "base_url": base_url,
        "runs_per_arm": runs,
        "records": records,
    }
    deferred: list[str] = []
    for model in models:
        try:
            for scenario in scenarios:
                for arm in ARMS:
                    prompt = build_prompt(arm, scenario)
                    fresh = 0
                    for run in range(runs):
                        if (model, scenario["id"], arm, run) in done:
                            continue
                        reply = call_model(client, base_url, api_key, model, prompt)
                        if sleep_between > 0:
                            time.sleep(sleep_between)
                        code = extract_code(reply)
                        constraint_results = [
                            evaluate_constraint(c, code) for c in scenario["constraints"]
                        ]
                        record = {
                            "model": model,
                            "scenario_id": scenario["id"],
                            "category": scenario["category"],
                            "arm": arm,
                            "run": run,
                            "constraints": constraint_results,
                        }
                        if any(c["violated"] for c in constraint_results):
                            record["raw_sample"] = reply
                        records.append(record)
                        fresh += 1
                    if fresh and checkpoint_path is not None:
                        _write_json(checkpoint_path, result)
                    if fresh:
                        print(f"[{model}] {scenario['id']} arm={arm} {runs}/{runs}", flush=True)
        except (httpx.HTTPStatusError, httpx.TimeoutException) as exc:
            # Retry exhaustion on this model (quota window). Checkpoint what we
            # have and move on to the next model; a later --resume pass fills
            # the gap instead of the whole matrix dying.
            if checkpoint_path is not None:
                _write_json(checkpoint_path, result)
            deferred.append(model)
            print(f"[{model}] DEFERRED after retry exhaustion: {exc}", flush=True)
    if deferred:
        result["deferred_models"] = deferred
    return result


def _write_json(path: str | Path, payload: dict) -> None:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)


def _load_scenarios_lenient(dir_path: str) -> list[dict]:
    """Missing scenarios dir is treated as an empty list (dry-run support)."""
    if not Path(dir_path).is_dir():
        return []
    return load_scenarios(dir_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m cvb.runner",
        description="Run the CVB matrix against an OpenAI-compatible API.",
    )
    parser.add_argument("--scenarios", default="scenarios", help="scenario dir")
    parser.add_argument("--runs", type=int, default=3, help="runs per arm")
    parser.add_argument("--json", dest="json_path", default=None, help="output JSON path")
    parser.add_argument("--models", default=None, help="comma-separated model ids (skips probe)")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--api-key-env", default="GROQ_API_KEY", help="env var holding the API key")
    parser.add_argument(
        "--scenario-id",
        action="append",
        default=None,
        help="run only this scenario id (repeatable)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="list scenario ids + resolved models without calling the API",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="skip cells already present in the --json file",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.0,
        help="seconds to sleep between calls (free-tier rate-limit politeness)",
    )
    args = parser.parse_args(argv)

    scenarios = _load_scenarios_lenient(args.scenarios)
    if args.scenario_id:
        wanted = set(args.scenario_id)
        missing = wanted - {s["id"] for s in scenarios}
        if missing:
            print("ERROR: unknown scenario id(s): " + ", ".join(sorted(missing)))
            return 2
        scenarios = [s for s in scenarios if s["id"] in wanted]

    if args.models:
        requested = [m.strip() for m in args.models.split(",") if m.strip()]
    else:
        requested = None

    if args.dry_run:
        print(f"scenarios ({len(scenarios)}):")
        for s in scenarios:
            print(f"  {s['id']} [{s['category']}]")
        if requested is not None:
            models = requested
            note = "from --models"
        else:
            models = PREFERRED_MODELS[:3]
            note = "preferred defaults; live run probes /models and picks first 3 available"
        print(f"models ({note}):")
        for m in models:
            print(f"  {m}")
        return 0

    api_key = os.environ.get(args.api_key_env, "")
    if not api_key:
        print(f"ERROR: API key env var {args.api_key_env} is not set")
        return 2
    if not scenarios:
        print(f"ERROR: no scenarios found in {args.scenarios}")
        return 2
    if not args.json_path:
        print("ERROR: --json output path is required for a live run")
        return 2

    existing_records: list[dict] = []
    if args.resume and Path(args.json_path).is_file():
        with open(args.json_path, encoding="utf-8") as fh:
            existing_records = json.load(fh).get("records", [])
        print(f"resuming: {len(existing_records)} records already present")

    with httpx.Client(timeout=60.0) as client:
        if requested is not None:
            models = requested
        else:
            models = probe_models(client, args.base_url, api_key, PREFERRED_MODELS)[:3]
        if not models:
            print("ERROR: no preferred models available at the endpoint")
            return 2
        print(f"running {len(models)} models x {len(scenarios)} scenarios x "
              f"{len(ARMS)} arms x {args.runs} runs", flush=True)
        result = run_matrix(
            models, scenarios, args.runs, client, args.base_url, api_key,
            existing_records=existing_records,
            checkpoint_path=args.json_path,
            sleep_between=args.sleep,
        )

    _write_json(args.json_path, result)
    print(f"wrote {len(result['records'])} records -> {args.json_path}")
    if result.get("deferred_models"):
        print("INCOMPLETE: deferred models: "
              + ", ".join(result["deferred_models"])
              + " (rerun with --resume to fill gaps)")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
