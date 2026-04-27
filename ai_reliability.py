"""Reliability checks for the PawPal+ AI Assistant.

The default checks are deterministic and local-first, so they do not spend
Gemini quota. A single live Gemini smoke test can be enabled explicitly.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from ai_assistant import ask_assistant


BASE_EVAL_TASKS: list[dict[str, Any]] = [
    {
        "title": "Morning walk",
        "duration_minutes": 20,
        "priority": "high",
        "recurrence": "daily",
        "completed": False,
        "start_time": "08:00",
    },
    {
        "title": "Feeding",
        "duration_minutes": 10,
        "priority": "high",
        "recurrence": "daily",
        "completed": False,
        "start_time": None,
    },
]


LOCAL_EVAL_CASES: list[dict[str, Any]] = [
    {
        "name": "local_add_daily_walk",
        "capability": "local task creation",
        "prompt": "Add a daily 20 minute morning walk for Mochi at 8am high priority",
        "expected_action": "add_task",
        "expected_source": "local",
        "tasks": [],
    },
    {
        "name": "local_add_natural_phrase",
        "capability": "local natural-language parsing",
        "prompt": "I need to brush Mochi for 15 minutes weekly",
        "expected_action": "add_task",
        "expected_source": "local",
        "tasks": [],
    },
    {
        "name": "local_complete_morning_walk",
        "capability": "local task completion",
        "prompt": "Mark morning walk done",
        "expected_action": "complete_task",
        "expected_source": "local",
        "tasks": BASE_EVAL_TASKS,
    },
    {
        "name": "local_remove_morning_walk",
        "capability": "local task removal",
        "prompt": "Remove morning walk",
        "expected_action": "remove_task",
        "expected_source": "local",
        "tasks": BASE_EVAL_TASKS,
    },
    {
        "name": "local_list_tasks",
        "capability": "local state question",
        "prompt": "Show my tasks",
        "expected_action": "answer_question",
        "expected_source": "local",
        "tasks": BASE_EVAL_TASKS,
    },
    {
        "name": "local_schedule_guidance",
        "capability": "schedule intent",
        "prompt": "Generate a schedule for today",
        "expected_action": "generate_schedule",
        "expected_source": "local",
        "tasks": BASE_EVAL_TASKS,
    },
]


LIVE_GEMINI_CASE: dict[str, Any] = {
    "name": "live_gemini_answer_question",
    "capability": "optional Gemini classifier",
    "prompt": "In one short sentence, what is PawPal?",
    "expected_action": "answer_question",
    "tasks": BASE_EVAL_TASKS,
}


LOCAL_RAG_CASE: dict[str, Any] = {
    "name": "local_rag_pet_care_question",
    "capability": "local knowledge base Q&A",
    "prompt": "How much exercise does my dog need?",
    "expected_action": "answer_question",
    "expected_source": "local_rag",
    "tasks": BASE_EVAL_TASKS,
}

MISSING_KEY_CASE: dict[str, Any] = {
    "name": "missing_key_unknown_question",
    "capability": "Gemini guardrail",
    "prompt": "What color is the best leash for a poodle?",
    "expected_action": "error",
    "expected_error_code": "missing_api_key",
    "tasks": BASE_EVAL_TASKS,
}


def _run_case(case: dict[str, Any], context: str, api_key: str) -> dict[str, Any]:
    """Run one reliability case and return a normalized result row."""
    response = ask_assistant(
        user_message=str(case["prompt"]),
        context=context,
        api_key=api_key,
        tasks=deepcopy(case.get("tasks", [])),
    )
    expected_action = str(case["expected_action"])
    actual_action = str(response.get("action", ""))
    expected_source = case.get("expected_source")
    expected_error_code = case.get("expected_error_code")
    actual_source = str(response.get("source", "gemini"))
    actual_error_code = response.get("error_code")
    passed = actual_action == expected_action
    if expected_source is not None:
        passed = passed and actual_source == expected_source
    if expected_error_code is not None:
        passed = passed and actual_error_code == expected_error_code

    return {
        "name": str(case["name"]),
        "capability": str(case.get("capability", "assistant behavior")),
        "prompt": str(case["prompt"]),
        "passed": passed,
        "expected_action": expected_action,
        "actual_action": actual_action,
        "message": str(response.get("message", "")),
        "source": actual_source,
        "expected_source": expected_source,
        "error_code": actual_error_code,
        "expected_error_code": expected_error_code,
    }


def run_reliability_checks(
    context: str,
    tasks: list[dict],
    api_key: str = "",
    include_live_gemini: bool = False,
) -> dict:
    """Run AI Assistant reliability checks and return a summary dict.

    The default local cases use fixed fixtures so the evaluation remains
    reproducible even when the user's current task list is empty or unusual.
    ``tasks`` is accepted for API symmetry with the app and future custom cases.
    """
    del tasks  # The default benchmark is intentionally fixture-based.

    cases = list(LOCAL_EVAL_CASES)
    cases.append(LOCAL_RAG_CASE)
    if not api_key:
        cases.append(MISSING_KEY_CASE)
    if include_live_gemini:
        cases.append(LIVE_GEMINI_CASE)

    results = [_run_case(case, context, api_key) for case in cases]
    total = len(results)
    passed = sum(1 for result in results if result["passed"])
    failed = total - passed
    pass_rate = passed / total if total else 0.0

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": pass_rate,
        "results": results,
    }
