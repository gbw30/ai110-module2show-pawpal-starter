from ai_assistant import build_context


def test_build_context_includes_owner_and_pet():
    """build_context must include owner name, pet name, species, and time budget."""
    ctx = build_context(
        owner_name="Jordan",
        pet_name="Mochi",
        species="dog",
        time_available=60,
        tasks=[],
    )
    assert "Jordan" in ctx
    assert "Mochi" in ctx
    assert "dog" in ctx
    assert "60" in ctx


def test_build_context_includes_tasks():
    """build_context must list each task with its details."""
    tasks = [
        {"title": "Morning walk", "duration_minutes": 30, "priority": "high",
         "recurrence": "daily", "completed": False, "start_time": "08:00"},
        {"title": "Feeding", "duration_minutes": 10, "priority": "high",
         "recurrence": None, "completed": True, "start_time": None},
    ]
    ctx = build_context(
        owner_name="Jordan",
        pet_name="Mochi",
        species="dog",
        time_available=60,
        tasks=tasks,
    )
    assert "Morning walk" in ctx
    assert "Feeding" in ctx
    assert "completed" in ctx.lower()


def test_build_context_empty_tasks():
    """build_context with no tasks should say there are no tasks."""
    ctx = build_context(
        owner_name="Jordan",
        pet_name="Mochi",
        species="dog",
        time_available=60,
        tasks=[],
    )
    assert "no tasks" in ctx.lower() or "0" in ctx


import json
import time as _time
import ai_assistant
from google.genai import errors


def test_rate_limit_rejects_rapid_calls():
    """ask_assistant must return an error dict if called within the cooldown window."""
    ai_assistant._next_allowed_ts = _time.time() + ai_assistant.COOLDOWN_SECONDS

    result = ai_assistant.ask_assistant(
        user_message="Is Mochi a good dog?",
        context="Owner: Jordan\nPet: Mochi (species: dog)",
        api_key="fake-key",
    )

    assert result["action"] == "error"
    assert "wait" in result["message"].lower() or "cooldown" in result["message"].lower()
    assert result["error_code"] == "cooldown"
    assert result["retry_after_seconds"] > 0


def test_rate_limit_allows_after_cooldown(monkeypatch):
    """ask_assistant must allow a call after the cooldown period has elapsed."""
    ai_assistant._next_allowed_ts = _time.time() - 1

    # Mock the Gemini client so we don't need a real API key
    # Gemini now returns "answer" not "message" (classifier-only mode)
    fake_response_text = json.dumps({
        "action": "answer_question",
        "tasks": [],
        "answer": "Mochi is a good dog!"
    })

    class FakeResponse:
        text = fake_response_text

    class FakeModels:
        def generate_content(self, **kwargs):
            return FakeResponse()

    class FakeClient:
        def __init__(self, **kwargs):
            self.models = FakeModels()

    monkeypatch.setattr("ai_assistant.genai.Client", FakeClient)

    result = ai_assistant.ask_assistant(
        user_message="Is Mochi a good dog?",
        context="Owner: Jordan\nPet: Mochi (species: dog)",
        api_key="fake-key",
    )

    assert result["action"] == "answer_question"
    assert result["message"] == "Mochi is a good dog!"


def test_local_add_task_does_not_call_gemini(monkeypatch):
    """Simple add-task requests should be handled locally to preserve free-tier quota."""
    ai_assistant._next_allowed_ts = _time.time() - 1

    class FakeClient:
        def __init__(self, **kwargs):
            raise AssertionError("Gemini should not be called for local task creation")

    monkeypatch.setattr("ai_assistant.genai.Client", FakeClient)

    result = ai_assistant.ask_assistant(
        user_message="Add a daily 20 minute morning walk for Mochi at 8am high priority",
        context="Owner: Jordan\nPet: Mochi (species: dog)",
        api_key="fake-key",
        tasks=[],
    )

    assert result["action"] == "add_task"
    assert result["source"] == "local"
    assert result["tasks"][0]["name"] == "morning walk"
    assert result["tasks"][0]["duration_minutes"] == 20
    assert result["tasks"][0]["priority"] == "high"
    assert result["tasks"][0]["recurrence"] == "daily"
    assert result["tasks"][0]["start_time"] == "08:00"


def test_local_complete_task_does_not_call_gemini(monkeypatch):
    """Simple complete-task requests should be handled locally."""
    ai_assistant._next_allowed_ts = _time.time() - 1

    class FakeClient:
        def __init__(self, **kwargs):
            raise AssertionError("Gemini should not be called for local completion")

    monkeypatch.setattr("ai_assistant.genai.Client", FakeClient)

    result = ai_assistant.ask_assistant(
        user_message="Mark morning walk done",
        context="Owner: Jordan\nPet: Mochi (species: dog)",
        api_key="fake-key",
        tasks=[
            {
                "title": "Morning walk",
                "duration_minutes": 20,
                "priority": "high",
                "completed": False,
            }
        ],
    )

    assert result["action"] == "complete_task"
    assert result["source"] == "local"
    assert result["tasks"] == [{"name": "Morning walk"}]


def test_local_natural_language_add_task(monkeypatch):
    """Natural phrasing like 'I need to walk my dog' should be handled locally."""
    ai_assistant._next_allowed_ts = _time.time() - 1

    class FakeClient:
        def __init__(self, **kwargs):
            raise AssertionError("Gemini should not be called")

    monkeypatch.setattr("ai_assistant.genai.Client", FakeClient)

    result = ai_assistant.ask_assistant(
        user_message="I need to walk my dog. It will take 30 minutes and is medium priority",
        context="Owner: Jordan\nPet: Mochi (species: dog)",
        api_key="fake-key",
        tasks=[],
    )

    assert result["action"] == "add_task"
    assert result["source"] == "local"
    assert result["tasks"][0]["duration_minutes"] == 30
    assert result["tasks"][0]["priority"] == "medium"
    assert result["tasks"][0]["name"]  # should have extracted a name


def test_ask_assistant_handles_invalid_json(monkeypatch):
    """ask_assistant must return an error dict when Gemini returns non-JSON."""
    ai_assistant._next_allowed_ts = _time.time() - 1

    class FakeResponse:
        text = "This is not JSON at all"

    class FakeModels:
        def generate_content(self, **kwargs):
            return FakeResponse()

    class FakeClient:
        def __init__(self, **kwargs):
            self.models = FakeModels()

    monkeypatch.setattr("ai_assistant.genai.Client", FakeClient)

    result = ai_assistant.ask_assistant(
        user_message="hello",
        context="Owner: Jordan",
        api_key="fake-key",
    )

    assert result["action"] == "error"
    assert "trouble" in result["message"].lower()


def test_ask_assistant_handles_api_exception(monkeypatch):
    """ask_assistant must return an error dict when the API call raises."""
    ai_assistant._next_allowed_ts = _time.time() - 1

    class FakeModels:
        def generate_content(self, **kwargs):
            raise RuntimeError("API quota exceeded")

    class FakeClient:
        def __init__(self, **kwargs):
            self.models = FakeModels()

    monkeypatch.setattr("ai_assistant.genai.Client", FakeClient)

    result = ai_assistant.ask_assistant(
        user_message="hello",
        context="Owner: Jordan",
        api_key="fake-key",
    )

    assert result["action"] == "error"
    assert "error" in result["message"].lower()


def test_ask_assistant_handles_gemini_429_and_blocks_next_call(monkeypatch):
    """Gemini 429 errors should report retry timing and prevent rapid retries."""
    ai_assistant._next_allowed_ts = _time.time() - 1
    call_count = {"count": 0}

    class FakeModels:
        def generate_content(self, **kwargs):
            call_count["count"] += 1
            raise errors.ClientError(
                429,
                {
                    "error": {
                        "code": 429,
                        "message": "Quota exceeded",
                        "status": "RESOURCE_EXHAUSTED",
                        "details": [
                            {
                                "@type": "type.googleapis.com/google.rpc.QuotaFailure",
                                "violations": [
                                    {
                                        "quotaMetric": (
                                            "generativelanguage.googleapis.com/"
                                            "generate_content_free_tier_requests"
                                        ),
                                        "quotaId": (
                                            "GenerateRequestsPerMinutePerProjectPerModel-"
                                            "FreeTier"
                                        ),
                                        "quotaDimensions": {
                                            "location": "global",
                                            "model": "gemini-2.0-flash",
                                        },
                                    }
                                ],
                            },
                            {
                                "@type": "type.googleapis.com/google.rpc.RetryInfo",
                                "retryDelay": "23s",
                            }
                        ],
                    }
                },
            )

    class FakeClient:
        def __init__(self, **kwargs):
            self.models = FakeModels()

    monkeypatch.setattr("ai_assistant.genai.Client", FakeClient)

    result = ai_assistant.ask_assistant(
        user_message="hello",
        context="Owner: Jordan",
        api_key="fake-key",
    )

    assert result["action"] == "error"
    assert result["error_code"] == "rate_limited"
    assert result["retry_after_seconds"] == 23
    assert "project rate limit" in result["message"].lower()
    assert "new api key" in result["message"].lower()
    assert result["quota_details"][0]["model"] == "gemini-2.0-flash"
    assert "free_tier_requests" in result["quota_details"][0]["quota_metric"]

    second_result = ai_assistant.ask_assistant(
        user_message="hello again",
        context="Owner: Jordan",
        api_key="fake-key",
    )

    assert second_result["action"] == "error"
    assert second_result["error_code"] == "cooldown"
    assert second_result["retry_after_seconds"] > 0
    assert call_count["count"] == 1
