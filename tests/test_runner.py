import json

import httpx

from cvb.runner import call_model, probe_models, run_matrix

SCENARIO = {
    "id": "s1", "category": "security", "task": "do a thing",
    "constraints": [{"id": "c1", "text": "parameterized sql only", "why": "injection incident",
                     "checks": [{"type": "regex_absent", "pattern": r"f\"SELECT", "description": "f-string sql"}]},
                    {"id": "c2", "text": "timeouts on calls", "why": "hang",
                     "checks": [{"type": "regex_present", "pattern": "timeout", "description": "no timeout"}]}],
}


def _transport(reply_text):
    def handler(request):
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": [{"id": "m-good"}, {"id": "m-other"}]})
        return httpx.Response(200, json={"choices": [{"message": {"content": reply_text}}]})
    return httpx.MockTransport(handler)


def test_call_model_returns_content():
    client = httpx.Client(transport=_transport("```python\nx=1\n```"))
    out = call_model(client, "https://x/v1", "k", "m", "prompt")
    assert "x=1" in out


def test_call_model_retries_on_429():
    calls = {"n": 0}
    def handler(request):
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(429, json={})
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})
    client = httpx.Client(transport=httpx.MockTransport(handler))
    assert call_model(client, "https://x/v1", "k", "m", "p", backoff_base=0) == "ok"
    assert calls["n"] == 3


def test_probe_models_preserves_preference_order():
    client = httpx.Client(transport=_transport(""))
    got = probe_models(client, "https://x/v1", "k", ["m-other", "m-missing", "m-good"])
    assert got == ["m-other", "m-good"]


def test_run_matrix_shape_and_scoring():
    reply = "```python\nquery = f\"SELECT * FROM t\"  # no timeout either\n```"
    client = httpx.Client(transport=_transport(reply))
    result = run_matrix(["m1"], [SCENARIO], runs=2, client=client, base_url="https://x/v1", api_key="k")
    recs = result["records"]
    assert len(recs) == 1 * 1 * 3 * 2  # models x scenarios x arms x runs
    r = recs[0]
    assert {c["constraint_id"] for c in r["constraints"]} == {"c1", "c2"}
    assert any(c["violated"] for c in r["constraints"])
    assert r["raw_sample"]  # violated -> sample kept
