from google.genai import errors

import ai_assistant
from ai_reliability import run_reliability_checks


CONTEXT = "Owner: Jordan\nDaily time available: 60 minutes\nPet: Mochi (species: dog)"


def test_run_reliability_checks_returns_summary():
    """The reliability harness must return aggregate scoring and case details."""
    summary = run_reliability_checks(CONTEXT, tasks=[], api_key="")

    assert summary["total"] == 8
    assert summary["passed"] == 8
    assert summary["failed"] == 0
    assert summary["pass_rate"] == 1.0
    assert len(summary["results"]) == 8
    assert {"total", "passed", "failed", "pass_rate", "results"} <= summary.keys()


def test_local_reliability_cases_cover_current_capabilities():
    """Default cases should match current local-first assistant capabilities."""
    summary = run_reliability_checks(CONTEXT, tasks=[], api_key="")
    actual = {result["name"]: result["actual_action"] for result in summary["results"]}

    assert actual["local_add_daily_walk"] == "add_task"
    assert actual["local_add_natural_phrase"] == "add_task"
    assert actual["local_complete_morning_walk"] == "complete_task"
    assert actual["local_remove_morning_walk"] == "remove_task"
    assert actual["local_list_tasks"] == "answer_question"
    assert actual["local_schedule_guidance"] == "generate_schedule"
    assert actual["local_rag_pet_care_question"] == "answer_question"
    assert actual["missing_key_unknown_question"] == "error"


def test_default_reliability_check_does_not_call_gemini(monkeypatch):
    """Default reliability checks must preserve free-tier quota."""
    class FakeClient:
        def __init__(self, **kwargs):
            raise AssertionError("Gemini should not be called by default reliability checks")

    monkeypatch.setattr("ai_assistant.genai.Client", FakeClient)

    summary = run_reliability_checks(CONTEXT, tasks=[], api_key="")

    assert summary["passed"] == summary["total"]
    local_results = [r for r in summary["results"] if r["name"].startswith("local_")]
    assert all(r["source"] in ("local", "local_rag") for r in local_results)
    missing_key = next(r for r in summary["results"] if r["name"] == "missing_key_unknown_question")
    assert missing_key["error_code"] == "missing_api_key"


def test_live_gemini_failure_only_fails_live_case(monkeypatch):
    """A live Gemini 429 should not change deterministic local case results."""
    ai_assistant._next_allowed_ts = 0.0

    class FakeModels:
        def generate_content(self, **kwargs):
            raise errors.ClientError(
                429,
                {
                    "error": {
                        "code": 429,
                        "message": "Quota exceeded",
                        "status": "RESOURCE_EXHAUSTED",
                    }
                },
            )

    class FakeClient:
        def __init__(self, **kwargs):
            self.models = FakeModels()

    monkeypatch.setattr("ai_assistant.genai.Client", FakeClient)

    summary = run_reliability_checks(
        CONTEXT,
        tasks=[],
        api_key="fake-key",
        include_live_gemini=True,
    )

    local_results = [r for r in summary["results"] if r["name"].startswith("local_")]
    live_result = next(r for r in summary["results"] if r["name"] == "live_gemini_answer_question")

    assert all(result["passed"] for result in local_results)
    assert live_result["passed"] is False
    assert live_result["actual_action"] == "error"
    assert live_result["error_code"] == "rate_limited"
    assert summary["total"] == 8
    assert summary["passed"] == 7
