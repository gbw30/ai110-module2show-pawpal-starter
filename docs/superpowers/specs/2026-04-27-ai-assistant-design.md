# AI Assistant Design — PawPal+

## Goal

Add an AI Assistant to PawPal+ that lets users type natural language requests (add tasks, ask pet-care questions, get schedule advice) and have Gemini act as a smart interface over the existing Scheduler — without replacing any scheduling logic.

## Architecture

### New file: ai_assistant.py

A pure-Python module with no Streamlit dependency. Responsibilities:

- Parse user intent locally for common task commands (~90% of requests) with
  zero API calls using regex-based intent matching.
- When local parsing fails, use Gemini as a lightweight intent classifier only
  (~200-token prompt, 150 max output tokens, temperature 0.0).
- Generate all user-facing messages locally from templates, not from Gemini.
- Build context from the user's current PawPal state (owner, pet, tasks).
- Enforce rate limiting (10-second cooldown between Gemini calls).
- Return a parsed dict to the caller. Never mutate external state.

#### Public API

```python
COOLDOWN_SECONDS: int = 10

def build_context(owner_name, pet_name, species, time_available, tasks, schedule_result=None) -> str
def ask_assistant(user_message: str, context: str, api_key: str, tasks: list[dict] | None = None) -> dict
```

`ask_assistant` first attempts local intent parsing via `_local_task_response()`.
If no local match is found, it falls back to a minimal Gemini classifier call.
On API error or rate-limit violation it returns `{"action": "error", "tasks": [], "message": "..."}`.

### Response JSON schema

Every Gemini response has this shape:

```json
{
  "action": "add_task | remove_task | complete_task | edit_task | generate_schedule | answer_question",
  "tasks": [
    {
      "name": "string",
      "duration_minutes": 30,
      "priority": "high | medium | low",
      "recurrence": "none | daily | weekly",
      "start_time": "HH:MM or null",
      "original_name": "string (edit_task only)"
    }
  ],
  "message": "Friendly explanation string"
}
```

- `action` — tells app.py what to do.
- `tasks` — payload for state-changing actions. Empty list for answer_question / generate_schedule.
- `message` — always present. Friendly explanation displayed to the user.

### app.py integration

A new "AI Assistant" section added after the Daily Schedule section.

Components:
- `st.text_input` for the user's natural language request.
- `st.button("Ask PawPal")` to submit.
- Rate-limit check using `st.session_state.last_ai_request` timestamp.
- Context built from current owner/pet/tasks state.
- Response validation before applying to `st.session_state.tasks`:
  - `add_task` — name non-empty, duration > 0, priority in {high, medium, low}.
  - `remove_task` — task name exists in session state.
  - `complete_task` — task exists and is incomplete.
  - `edit_task` — original_name exists, new values valid.
  - `generate_schedule` / `answer_question` — no state mutation, display message only.
- Valid changes applied to `st.session_state.tasks`.
- Result displayed via `st.success` / `st.info` / `st.warning`.

### Workflow

1. User types a request in the text input.
2. Local parser attempts to match the intent (add, remove, complete, list, schedule).
3. If matched locally: structured response returned with zero API calls.
4. If unmatched: one minimal Gemini call classifies the intent and extracts fields.
5. All user-facing messages are generated locally from templates.
6. app.py validates the returned data.
7. Valid changes are applied to session state by app.py (not by Gemini).
8. The existing Scheduler runs normally when the user clicks "Generate schedule".

### Dependencies

- `google-genai` added to requirements.txt.
- `GOOGLE_API_KEY` environment variable (loaded from .env via `os.environ`).
- If the key is missing, the AI Assistant section shows a warning and disables input.

### Rate limiting

Module-level timestamp tracking. `ask_assistant` checks elapsed time since last call and returns an error dict if under the 10-second cooldown. No external rate-limiting library needed.

### What this does NOT do

- Gemini never imports Streamlit or touches session state.
- Gemini never replaces the Scheduler's generate_plan / detect_conflicts logic.
- No separate knowledge document — Gemini uses its training knowledge grounded in the user's live PawPal context.
- No multi-turn conversation state — each request is independent.

## Documentation updates

After implementation:
- Update `current_design.md` to include the AI Assistant in the class/module diagram and design notes.
- Update `README.md` to document the AI Assistant feature, setup (API key), and usage.
