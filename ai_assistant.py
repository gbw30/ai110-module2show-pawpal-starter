"""PawPal+ AI Assistant — Gemini-powered natural language interface over Scheduler.

This module handles all Gemini API interaction. It does NOT import Streamlit
or mutate any external state. app.py calls ask_assistant(), validates the
structured response, and applies changes to session state itself.
"""

from __future__ import annotations

import json
import time as _time

from google import genai

COOLDOWN_SECONDS: int = 10
_last_request_ts: float = 0.0


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


SYSTEM_PROMPT = """\
You are PawPal+, a friendly AI pet-care assistant. You help pet owners manage \
daily care tasks for their pets.

You will receive the owner's current PawPal state (pet info, tasks, schedule). \
Based on the user's natural language request, respond with a JSON object.

RESPONSE FORMAT (always valid JSON, no markdown fences):
{
  "action": "add_task" | "remove_task" | "complete_task" | "edit_task" | "generate_schedule" | "answer_question",
  "tasks": [
    {
      "name": "string",
      "duration_minutes": integer,
      "priority": "high" | "medium" | "low",
      "recurrence": "none" | "daily" | "weekly",
      "start_time": "HH:MM" or null,
      "original_name": "string (only for edit_task, the current name of the task to edit)"
    }
  ],
  "message": "Friendly explanation of what you did and why"
}

RULES:
- action: pick the single best action for the request.
- tasks: list of task objects for add/remove/complete/edit actions. Empty list [] for answer_question and generate_schedule.
- For remove_task and complete_task: only "name" is required in each task object.
- For edit_task: include "original_name" (current name) plus the updated fields.
- message: always present. Explain what you're suggesting and why, in friendly language. \
  If suggesting tasks, explain why you chose that priority/duration. \
  If answering a question, ground your answer in the pet's species and current schedule.
- Use your knowledge of pet care to suggest reasonable durations and priorities.
- If the request is ambiguous, pick the most likely interpretation and explain your reasoning in the message.
- Respond ONLY with the JSON object. No markdown, no extra text.
"""


def ask_assistant(user_message: str, context: str, api_key: str) -> dict:
    """Send a single request to Gemini and return the structured response dict.

    Returns {"action": "error", "tasks": [], "message": "..."} on any failure.
    """
    global _last_request_ts

    # Rate limiting
    now = _time.time()
    elapsed = now - _last_request_ts
    if elapsed < COOLDOWN_SECONDS:
        remaining = int(COOLDOWN_SECONDS - elapsed) + 1
        return {
            "action": "error",
            "tasks": [],
            "message": f"Please wait {remaining} seconds before asking again (cooldown).",
        }

    try:
        client = genai.Client(api_key=api_key)
        prompt = f"CURRENT PAWPAL STATE:\n{context}\n\nUSER REQUEST:\n{user_message}"
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config={"system_instruction": SYSTEM_PROMPT},
        )

        _last_request_ts = _time.time()

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
        result.setdefault("message", "Done.")

        return result

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
