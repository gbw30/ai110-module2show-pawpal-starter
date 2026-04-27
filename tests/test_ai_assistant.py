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


def test_rate_limit_rejects_rapid_calls():
    """ask_assistant must return an error dict if called within the cooldown window."""
    ai_assistant._last_request_ts = _time.time()

    result = ai_assistant.ask_assistant(
        user_message="Add a walk",
        context="Owner: Jordan\nPet: Mochi (species: dog)",
        api_key="fake-key",
    )

    assert result["action"] == "error"
    assert "wait" in result["message"].lower() or "cooldown" in result["message"].lower()


def test_rate_limit_allows_after_cooldown(monkeypatch):
    """ask_assistant must allow a call after the cooldown period has elapsed."""
    ai_assistant._last_request_ts = _time.time() - ai_assistant.COOLDOWN_SECONDS - 1

    # Mock the Gemini client so we don't need a real API key
    fake_response_text = json.dumps({
        "action": "answer_question",
        "tasks": [],
        "message": "Mochi is a good dog!"
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


def test_ask_assistant_handles_invalid_json(monkeypatch):
    """ask_assistant must return an error dict when Gemini returns non-JSON."""
    ai_assistant._last_request_ts = _time.time() - ai_assistant.COOLDOWN_SECONDS - 1

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
    ai_assistant._last_request_ts = _time.time() - ai_assistant.COOLDOWN_SECONDS - 1

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
