"""PawPal+ AI Assistant — Gemini-powered natural language interface over Scheduler.

This module handles all Gemini API interaction. It does NOT import Streamlit
or mutate any external state. app.py calls ask_assistant(), validates the
structured response, and applies changes to session state itself.
"""

from __future__ import annotations

import json
import time as _time

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
