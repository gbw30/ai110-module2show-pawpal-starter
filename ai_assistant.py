"""PawPal+ AI Assistant — Gemini-powered natural language interface over Scheduler.

This module handles all Gemini API interaction. It does NOT import Streamlit
or mutate any external state. app.py calls ask_assistant(), validates the
structured response, and applies changes to session state itself.
"""

from __future__ import annotations

import json
import math
import os
import re
import time as _time

from google import genai
from google.genai import errors

COOLDOWN_SECONDS: int = 10
RATE_LIMIT_FALLBACK_SECONDS: int = 60
DEFAULT_GEMINI_MODEL: str = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash-lite")
MAX_GEMINI_CONTEXT_CHARS: int = 4000
_next_allowed_ts: float = 0.0


def build_context(
    owner_name: str,
    pet_name: str,
    species: str,
    time_available: int,
    tasks: list[dict],
    schedule_result: dict | None = None,
) -> str:
    """Serialize current PawPal state into a text block for the Gemini prompt."""
    lines = [
        f"Owner: {owner_name}",
        f"Daily time available: {time_available} minutes",
        f"Pet: {pet_name} (species: {species})",
        "",
    ]

    if not tasks:
        lines.append("Current tasks: none (0 tasks)")
    else:
        lines.append(f"Current tasks ({len(tasks)}):")
        for t in tasks:
            status = "completed" if t.get("completed", False) else "incomplete"
            recur = f", recurrence: {t['recurrence']}" if t.get("recurrence") else ""
            start = f", start_time: {t['start_time']}" if t.get("start_time") else ""
            lines.append(
                f"  - {t['title']} | {t['duration_minutes']} min | "
                f"priority: {t['priority']} | {status}{recur}{start}"
            )

    if schedule_result:
        lines.append("")
        lines.append(f"Last schedule: {json.dumps(schedule_result)}")

    return "\n".join(lines)


CLASSIFIER_PROMPT = """\
Classify this pet-care request. Return ONLY a JSON object, no markdown.
{"action":"add_task|remove_task|complete_task|edit_task|generate_schedule|answer_question",\
"tasks":[{"name":"str","duration_minutes":int,"priority":"high|medium|low",\
"recurrence":"none|daily|weekly","start_time":"HH:MM or null",\
"original_name":"str (edit_task only)"}],\
"answer":"str (answer_question only, 1-2 sentences)"}
For remove/complete: tasks needs only "name". Empty tasks list for answer/schedule.
"""


def _parse_delay_seconds(value: object) -> int | None:
    """Parse retry delay values like '21s', '45.1s', or 30 into seconds."""
    if isinstance(value, (int, float)):
        return max(1, math.ceil(value))
    if not isinstance(value, str):
        return None

    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)s?\s*", value)
    if match is None:
        return None
    return max(1, math.ceil(float(match.group(1))))


def _find_retry_delay_seconds(value: object) -> int | None:
    """Find a retryDelay field in a nested Gemini error payload."""
    if isinstance(value, dict):
        direct = _parse_delay_seconds(value.get("retryDelay"))
        if direct is not None:
            return direct
        for child in value.values():
            nested = _find_retry_delay_seconds(child)
            if nested is not None:
                return nested
    elif isinstance(value, list):
        for child in value:
            nested = _find_retry_delay_seconds(child)
            if nested is not None:
                return nested
    return None


def _retry_after_from_error(error: errors.ClientError) -> int:
    """Return Gemini's suggested retry delay, or a conservative fallback."""
    retry_delay = _find_retry_delay_seconds(getattr(error, "details", None))
    if retry_delay is not None:
        return retry_delay

    response = getattr(error, "response", None)
    headers = getattr(response, "headers", None)
    if headers:
        header_delay = _parse_delay_seconds(headers.get("retry-after"))
        if header_delay is not None:
            return header_delay

    return RATE_LIMIT_FALLBACK_SECONDS


def _collect_quota_violations(value: object) -> list[dict[str, str]]:
    """Extract sanitized quota failure details from a Gemini error payload."""
    quota_details: list[dict[str, str]] = []

    if isinstance(value, dict):
        violations = value.get("violations")
        if isinstance(violations, list):
            for violation in violations:
                if not isinstance(violation, dict):
                    continue
                dimensions = violation.get("quotaDimensions") or {}
                detail = {
                    "quota_metric": str(violation.get("quotaMetric", "")),
                    "quota_id": str(violation.get("quotaId", "")),
                    "model": str(dimensions.get("model", "")),
                    "location": str(dimensions.get("location", "")),
                }
                quota_details.append({k: v for k, v in detail.items() if v})

        for child in value.values():
            quota_details.extend(_collect_quota_violations(child))
    elif isinstance(value, list):
        for child in value:
            quota_details.extend(_collect_quota_violations(child))

    return quota_details


def _format_quota_details(quota_details: list[dict[str, str]]) -> str:
    """Format a short quota detail summary for the app error message."""
    if not quota_details:
        return ""

    lines = []
    for detail in quota_details[:3]:
        parts = []
        if detail.get("quota_metric"):
            parts.append(detail["quota_metric"])
        if detail.get("model"):
            parts.append(f"model={detail['model']}")
        if detail.get("quota_id"):
            parts.append(f"quota={detail['quota_id']}")
        if detail.get("location"):
            parts.append(f"location={detail['location']}")
        if parts:
            lines.append("; ".join(parts))

    if len(quota_details) > 3:
        lines.append(f"{len(quota_details) - 3} more quota detail(s) omitted")

    return " Gemini quota detail: " + " | ".join(lines) if lines else ""


def _rate_limit_error(
    retry_after_seconds: int,
    quota_details: list[dict[str, str]] | None = None,
    gemini_error_message: str | None = None,
) -> dict:
    """Build a user-facing Gemini 429 response."""
    quota_details = quota_details or []
    message = (
        "Gemini hit a project rate limit or quota limit "
        "(429 RESOURCE_EXHAUSTED). "
        f"Please wait about {retry_after_seconds} seconds before trying again. "
        "Creating a new API key under the same Google Cloud project does not "
        "reset Gemini quota."
    )
    message += _format_quota_details(quota_details)

    return {
        "action": "error",
        "tasks": [],
        "message": message,
        "error_code": "rate_limited",
        "retry_after_seconds": retry_after_seconds,
        "quota_details": quota_details,
        "gemini_error_message": gemini_error_message,
    }


def _extract_pet_name(context: str) -> str | None:
    match = re.search(r"^Pet:\s*([^(]+)", context, flags=re.MULTILINE)
    return match.group(1).strip() if match else None


def _extract_duration_minutes(message: str) -> int | None:
    hour_match = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h)\b", message, re.I)
    minute_match = re.search(r"\b(\d+)\s*(?:minutes?|mins?|m)\b", message, re.I)
    total = 0
    if hour_match:
        total += round(float(hour_match.group(1)) * 60)
    if minute_match:
        total += int(minute_match.group(1))
    return total or None


def _extract_priority(message: str) -> str:
    lowered = message.lower()
    if re.search(r"\b(high|urgent|critical|important|medication|medicine|insulin)\b", lowered):
        return "high"
    if re.search(r"\b(low|optional|whenever)\b", lowered):
        return "low"
    if re.search(r"\b(medium|normal|regular)\b", lowered):
        return "medium"
    return "medium"


def _extract_recurrence(message: str) -> str | None:
    lowered = message.lower()
    if re.search(r"\b(daily|every day|each day)\b", lowered):
        return "daily"
    if re.search(r"\b(weekly|every week|each week)\b", lowered):
        return "weekly"
    return None


def _format_time(hour: int, minute: int = 0) -> str:
    return f"{hour:02d}:{minute:02d}"


def _extract_start_time(message: str) -> str | None:
    clock_24 = re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", message)
    if clock_24:
        return _format_time(int(clock_24.group(1)), int(clock_24.group(2)))

    clock_12 = re.search(r"\b(1[0-2]|0?[1-9])(?::([0-5]\d))?\s*([ap])\.?m\.?\b", message, re.I)
    if not clock_12:
        return None

    hour = int(clock_12.group(1))
    minute = int(clock_12.group(2) or 0)
    meridiem = clock_12.group(3).lower()
    if meridiem == "p" and hour != 12:
        hour += 12
    if meridiem == "a" and hour == 12:
        hour = 0
    return _format_time(hour, minute)


def _strip_task_details(message: str, pet_name: str | None) -> str:
    name = message.strip()
    name = re.sub(
        r"^\s*(please\s+)?"
        r"(i\s+(need|want|have|should|got?ta|will|am going)\s+to\s+)?"
        r"(add|create|schedule|make|set up|do|take|give|start|go for|go on)?\s*",
        "", name, flags=re.I,
    )
    name = re.sub(r"\b(an?|the)\s+task\s+(called|named)\s+", "", name, flags=re.I)
    name = re.sub(r"\bit\s+(will|should|would)\s+take\b", "", name, flags=re.I)
    name = re.sub(r"\b(and\s+)?(is|it'?s|that'?s)\s+(a\s+)?(high|medium|low|urgent|normal)\s*(priority)?\b", "", name, flags=re.I)
    name = re.sub(r"\b\d+(?:\.\d+)?\s*(?:hours?|hrs?|h)\b", "", name, flags=re.I)
    name = re.sub(r"\b\d+\s*(?:minutes?|mins?|m)\b", "", name, flags=re.I)
    name = re.sub(r"\b(high|medium|low|urgent|critical|important|normal|regular|optional)\s+priority\b", "", name, flags=re.I)
    name = re.sub(r"\b(make it|as)\s+(high|medium|low|urgent|normal|optional)\b", "", name, flags=re.I)
    name = re.sub(r"\b(daily|weekly|every day|each day|every week|each week)\b", "", name, flags=re.I)
    name = re.sub(r"\bat\s+(?:[01]?\d|2[0-3]):[0-5]\d\b", "", name, flags=re.I)
    name = re.sub(r"\bat\s+(?:1[0-2]|0?[1-9])(?::[0-5]\d)?\s*[ap]\.?m\.?\b", "", name, flags=re.I)
    if pet_name:
        name = re.sub(rf"\bfor\s+{re.escape(pet_name)}\b", "", name, flags=re.I)
    name = re.sub(r"\bfor\s+(my\s+)?(dog|cat|pet)\b", "", name, flags=re.I)
    name = re.sub(r"[-,.;:]+", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    name = re.sub(r"^(an?|the)\s+", "", name, flags=re.I)
    return name


def _find_task_name(message: str, tasks: list[dict]) -> str | None:
    lowered = message.lower()
    for task in sorted(tasks, key=lambda t: len(str(t.get("title", ""))), reverse=True):
        title = str(task.get("title", "")).strip()
        if title and title.lower() in lowered:
            return title
    return None


def _local_task_response(user_message: str, context: str, tasks: list[dict]) -> dict | None:
    """Handle simple assistant intents without spending Gemini quota."""
    lowered = user_message.lower().strip()
    pet_name = _extract_pet_name(context)

    if re.search(r"\b(what|show|list)\b.*\b(tasks?|todos?|to dos)\b", lowered):
        incomplete = [t for t in tasks if not t.get("completed", False)]
        if not tasks:
            message = "You do not have any PawPal tasks yet."
        elif incomplete:
            names = ", ".join(str(t["title"]) for t in incomplete)
            message = f"You have {len(incomplete)} incomplete task(s): {names}."
        else:
            message = "All current PawPal tasks are completed."
        return {"action": "answer_question", "tasks": [], "message": message, "source": "local"}

    if re.search(r"\b(generate|build|make|show)\b.*\b(schedule|plan)\b", lowered):
        return {
            "action": "generate_schedule",
            "tasks": [],
            "message": "Use the Generate schedule button to build the latest plan from your current tasks.",
            "source": "local",
        }

    if re.search(r"\b(remove|delete)\b", lowered):
        name = _find_task_name(user_message, tasks)
        if not name:
            return {
                "action": "error",
                "tasks": [],
                "message": "I can remove tasks locally, but I need the exact task name.",
                "source": "local",
            }
        return {
            "action": "remove_task",
            "tasks": [{"name": name}],
            "message": f'Removed "{name}" from your PawPal tasks.',
            "source": "local",
        }

    if re.search(r"\b(complete|done|finished|mark)\b", lowered):
        name = _find_task_name(user_message, tasks)
        if not name:
            return {
                "action": "error",
                "tasks": [],
                "message": "I can mark tasks complete locally, but I need the exact task name.",
                "source": "local",
            }
        return {
            "action": "complete_task",
            "tasks": [{"name": name}],
            "message": f'Marked "{name}" complete.',
            "source": "local",
        }

    _ADD_INTENT = (
        r"\b(add|create|schedule|set up)\b"
        r"|\bi\s+(need|want|have|should|got?ta|will|am going)\s+to\b"
        r"|\b(it'?s|that'?s)\s+time\s+(for|to)\b"
        r"|\b(go for|go on|take|give|start|do)\s+(a\s+)?\w"
    )
    if re.search(_ADD_INTENT, lowered) and _extract_duration_minutes(user_message) is not None:
        duration = _extract_duration_minutes(user_message)
        name = _strip_task_details(user_message, pet_name)
        if not name:
            return {
                "action": "error",
                "tasks": [],
                "message": (
                    "I can add tasks without using Gemini when you include a task name "
                    "and duration, like: Add 20 min morning walk."
                ),
                "source": "local",
            }

        recurrence = _extract_recurrence(user_message)
        priority = _extract_priority(user_message)
        start_time = _extract_start_time(user_message)
        return {
            "action": "add_task",
            "tasks": [
                {
                    "name": name,
                    "duration_minutes": duration,
                    "priority": priority,
                    "recurrence": recurrence or "none",
                    "start_time": start_time,
                }
            ],
            "message": f'Added "{name}" locally without using Gemini quota.',
            "source": "local",
        }

    return None


def _format_message(action: str, tasks: list[dict]) -> str:
    """Generate a user-facing message locally from the classified action."""
    if action == "add_task" and tasks:
        parts = []
        for t in tasks:
            name = t.get("name", "task")
            dur = t.get("duration_minutes", "?")
            pri = t.get("priority", "medium")
            parts.append(f'"{name}" ({dur} min, {pri} priority)')
        return "Added " + ", ".join(parts) + "."
    if action == "remove_task" and tasks:
        names = ", ".join(f'"{t.get("name", "task")}"' for t in tasks)
        return f"Removed {names}."
    if action == "complete_task" and tasks:
        names = ", ".join(f'"{t.get("name", "task")}"' for t in tasks)
        return f"Marked {names} complete."
    if action == "edit_task" and tasks:
        names = ", ".join(f'"{t.get("original_name", "task")}"' for t in tasks)
        return f"Updated {names}."
    if action == "generate_schedule":
        return "Use the Generate schedule button to build the latest plan."
    return "Done."


def _compact_context(context: str) -> str:
    if len(context) <= MAX_GEMINI_CONTEXT_CHARS:
        return context
    return context[:MAX_GEMINI_CONTEXT_CHARS] + "\n...context shortened for free-tier usage..."


def ask_assistant(
    user_message: str,
    context: str,
    api_key: str,
    tasks: list[dict] | None = None,
) -> dict:
    """Send a single request to Gemini and return the structured response dict.

    Returns {"action": "error", "tasks": [], "message": "..."} on any failure.
    """
    local_result = _local_task_response(user_message, context, tasks or [])
    if local_result is not None:
        return local_result

    if not api_key:
        return {
            "action": "error",
            "tasks": [],
            "message": (
                "Set GOOGLE_API_KEY to use Gemini-backed pet-care questions. "
                "Local task commands still work without an API key."
            ),
            "error_code": "missing_api_key",
        }

    global _next_allowed_ts

    # Rate limiting
    now = _time.time()
    if now < _next_allowed_ts:
        remaining = max(1, math.ceil(_next_allowed_ts - now))
        return {
            "action": "error",
            "tasks": [],
            "message": f"Please wait {remaining} seconds before asking again (cooldown).",
            "error_code": "cooldown",
            "retry_after_seconds": remaining,
        }

    _next_allowed_ts = now + COOLDOWN_SECONDS

    try:
        client = genai.Client(api_key=api_key)
        prompt = f"STATE:\n{_compact_context(context)}\n\nREQUEST:\n{user_message}"
        response = client.models.generate_content(
            model=DEFAULT_GEMINI_MODEL,
            contents=prompt,
            config={
                "system_instruction": CLASSIFIER_PROMPT,
                "max_output_tokens": 150,
                "temperature": 0.0,
            },
        )

        # Parse JSON from response
        text = response.text.strip()
        # Strip markdown fences if Gemini adds them despite instructions
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3].strip()
        if text.startswith("json"):
            text = text[4:].strip()

        result = json.loads(text)

        # Ensure required keys exist
        result.setdefault("action", "answer_question")
        result.setdefault("tasks", [])

        # Generate message locally — Gemini only classifies
        if result["action"] == "answer_question":
            result["message"] = result.pop("answer", "I'm not sure how to help with that.")
        else:
            result["message"] = _format_message(result["action"], result["tasks"])
        result["source"] = "gemini"

        return result

    except errors.ClientError as e:
        if e.code == 429:
            retry_after_seconds = _retry_after_from_error(e)
            quota_details = _collect_quota_violations(getattr(e, "details", None))
            _next_allowed_ts = _time.time() + retry_after_seconds
            return _rate_limit_error(retry_after_seconds, quota_details, e.message)

        return {
            "action": "error",
            "tasks": [],
            "message": f"AI assistant error: {e}",
        }
    except json.JSONDecodeError:
        return {
            "action": "error",
            "tasks": [],
            "message": "Sorry, I had trouble understanding the response. Please try again.",
        }
    except Exception as e:
        return {
            "action": "error",
            "tasks": [],
            "message": f"AI assistant error: {e}",
        }
