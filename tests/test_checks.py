from cvb.checks import evaluate_check, evaluate_constraint, extract_code


def test_extract_code_fenced():
    text = "Here you go:\n```python\nimport httpx\n```\ntrailing prose"
    assert extract_code(text) == "import httpx"


def test_extract_code_multiple_fences_joined():
    text = "```python\na = 1\n```\nand\n```\nb = 2\n```"
    assert extract_code(text) == "a = 1\nb = 2"


def test_extract_code_no_fence_returns_all():
    assert extract_code("import os") == "import os"


def test_regex_absent_violation():
    check = {"type": "regex_absent", "pattern": r"\bimport requests\b", "description": "uses requests"}
    assert evaluate_check(check, "import requests") is True
    assert evaluate_check(check, "import httpx") is False


def test_regex_present_violation():
    check = {"type": "regex_present", "pattern": r"encoding\s*=", "description": "missing encoding"}
    assert evaluate_check(check, "open('f')") is True
    assert evaluate_check(check, "open('f', encoding='utf-8')") is False


def test_regex_absent_unless():
    check = {"type": "regex_absent_unless", "pattern": r"open\([^)]*\)", "unless": "encoding=", "description": "open without encoding"}
    assert evaluate_check(check, "open('f', encoding='utf-8')") is False
    assert evaluate_check(check, "open('f')") is True


def test_evaluate_constraint_any_check_violates():
    constraint = {
        "id": "c1",
        "text": "never use requests",
        "checks": [
            {"type": "regex_absent", "pattern": r"import requests", "description": "imports requests"},
            {"type": "regex_absent", "pattern": r"from requests", "description": "from-imports requests"},
        ],
    }
    result = evaluate_constraint(constraint, "from requests import get")
    assert result == {"constraint_id": "c1", "violated": True, "failed_checks": ["from-imports requests"]}
    clean = evaluate_constraint(constraint, "import httpx")
    assert clean["violated"] is False and clean["failed_checks"] == []
