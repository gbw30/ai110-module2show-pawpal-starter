# AI Assistant Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Gemini-powered AI Assistant to PawPal+ that converts natural language into structured scheduler actions, with the existing Scheduler remaining the source of truth.

**Architecture:** A new `ai_assistant.py` module handles all Gemini interaction — building context, making one API call per request, enforcing rate limits, and returning a validated dict. `app.py` receives the dict, validates the payload, applies changes to session state, and displays the friendly message. Gemini never touches session state directly.

**Tech Stack:** Python 3.10+, google-generativeai SDK, Streamlit, existing pawpal_system.py domain model.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `ai_assistant.py` | Create | Gemini API wrapper: build context, single-call structured output, rate limiting |
| `tests/test_ai_assistant.py` | Create | Unit tests for context building, response parsing, rate limiting, validation |
| `app.py` | Modify (append after line 329) | New "AI Assistant" UI section |
| `requirements.txt` | Modify | Add `google-generativeai>=0.8` |
| `.gitignore` | Modify | Add `.env` if not already ignored |
| `current_design.md` | Modify | Add AI Assistant to design docs |
| `README.md` | Modify | Document feature, setup, usage |

---

### Task 1: Install dependency and secure API key

**Files:**
- Modify: `requirements.txt`
- Modify: `.gitignore`

- [ ] **Step 1: Add google-generativeai to requirements.txt**

```
streamlit>=1.30
pytest>=7.0
google-generativeai>=0.8
```

- [ ] **Step 2: Add .env to .gitignore**

Append `.env` to `.gitignore` if not already present. Current `.gitignore`:
```
__pycache__/
.venv/
.venv_new/
.pytest_cache/
.DS_Store
```

Add:
```
.env
```

- [ ] **Step 3: Install the dependency**

Run: `pip install -r requirements.txt`
Expected: `google-generativeai` installs successfully.

- [ ] **Step 4: Verify import works**

Run: `python -c "import google.generativeai; print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add requirements.txt .gitignore
git commit -m "chore: add google-generativeai dependency and secure .env"
```

---

### Task 2: Create ai_assistant.py — context builder

**Files:**
- Create: `ai_assistant.py`
- Create: `tests/test_ai_assistant.py`

- [ ] **Step 1: Write the failing test for build_context**

```python
# tests/test_ai_assistant.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ai_assistant.py -v`
Expected: FAIL — `ImportError: cannot import name 'build_context' from 'ai_assistant'`

- [ ] **Step 3: Implement build_context**

```python
# ai_assistant.py
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

PRIORITY_LABELS = {"high": "high", "medium": "medium", "low": "low"}


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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ai_assistant.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add ai_assistant.py tests/test_ai_assistant.py
git commit -m "feat: add build_context for AI assistant"
```

---

### Task 3: Create ai_assistant.py — ask_assistant with rate limiting

**Files:**
- Modify: `ai_assistant.py`
- Modify: `tests/test_ai_assistant.py`

- [ ] **Step 1: Write the failing test for rate limiting**

Append to `tests/test_ai_assistant.py`:

```python
import ai_assistant


def test_rate_limit_rejects_rapid_calls(monkeypatch):
    """ask_assistant must return an error dict if called within the cooldown window."""
    # Pretend a request just happened
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
    import time as _time_mod
    ai_assistant._last_request_ts = _time_mod.time() - ai_assistant.COOLDOWN_SECONDS - 1

    # Mock the actual Gemini call so we don't need a real API key
    def fake_generate(self, contents, **kwargs):
        class FakeResponse:
            text = json.dumps({
                "action": "answer_question",
                "tasks": [],
                "message": "Mochi is a good dog!"
            })
        return FakeResponse()

    monkeypatch.setattr(
        "google.generativeai.GenerativeModel.generate_content",
        fake_generate,
    )

    result = ai_assistant.ask_assistant(
        user_message="Is Mochi a good dog?",
        context="Owner: Jordan\nPet: Mochi (species: dog)",
        api_key="fake-key",
    )

    assert result["action"] == "answer_question"
    assert result["message"] == "Mochi is a good dog!"
```

Add this import at the top of the test file:

```python
import json
import time as _time
```

- [ ] **Step 2: Run tests to verify the new tests fail**

Run: `python -m pytest tests/test_ai_assistant.py::test_rate_limit_rejects_rapid_calls tests/test_ai_assistant.py::test_rate_limit_allows_after_cooldown -v`
Expected: FAIL — `AttributeError: module 'ai_assistant' has no attribute 'ask_assistant'`

- [ ] **Step 3: Implement ask_assistant with rate limiting and Gemini call**

Append to `ai_assistant.py`:

```python
import google.generativeai as genai


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
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            "gemini-2.0-flash",
            system_instruction=SYSTEM_PROMPT,
        )

        prompt = f"CURRENT PAWPAL STATE:\n{context}\n\nUSER REQUEST:\n{user_message}"
        response = model.generate_content(prompt)

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
```

- [ ] **Step 4: Run all tests to verify they pass**

Run: `python -m pytest tests/test_ai_assistant.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add ai_assistant.py tests/test_ai_assistant.py
git commit -m "feat: add ask_assistant with Gemini call and rate limiting"
```

---

### Task 4: Add AI Assistant section to app.py

**Files:**
- Modify: `app.py` (append after line 329)

- [ ] **Step 1: Add imports to app.py**

At the top of `app.py`, after the existing imports (line 1-6), add:

```python
import os
from ai_assistant import ask_assistant, build_context
```

- [ ] **Step 2: Add the AI Assistant section**

Append after line 329 (end of file):

```python

st.divider()

# ── AI Assistant ─────────────────────────────────────────────────────────────

st.subheader("AI Assistant")
st.caption(
    "Ask in plain English — add tasks, get schedule advice, or ask pet-care questions."
)

api_key = os.environ.get("GOOGLE_API_KEY", "")

if not api_key:
    st.warning(
        "Set the GOOGLE_API_KEY environment variable (in your .env file) to enable the AI assistant."
    )
else:
    if "last_ai_request" not in st.session_state:
        st.session_state.last_ai_request = 0.0
    if "ai_response" not in st.session_state:
        st.session_state.ai_response = None

    user_message = st.text_input(
        "What would you like to do?",
        placeholder="e.g. Add a 30-minute morning walk for Mochi",
        key="ai_input",
    )

    if st.button("Ask PawPal", type="primary", key="ai_submit"):
        if not user_message.strip():
            st.warning("Please type a request first.")
        else:
            context = build_context(
                owner_name=owner_name,
                pet_name=pet_name,
                species=species,
                time_available=int(time_available),
                tasks=st.session_state.tasks,
            )

            result = ask_assistant(user_message, context, api_key)
            st.session_state.ai_response = result

            if result["action"] == "error":
                st.error(result["message"])
            elif result["action"] in ("answer_question", "generate_schedule"):
                st.info(result["message"])
            elif result["action"] == "add_task":
                added = []
                rejected = []
                for task in result.get("tasks", []):
                    name = str(task.get("name", "")).strip()
                    dur = task.get("duration_minutes", 0)
                    pri = str(task.get("priority", "medium")).lower()
                    recur = task.get("recurrence")
                    start = task.get("start_time")

                    # Validation
                    if not name:
                        rejected.append("Task with empty name skipped.")
                        continue
                    if not isinstance(dur, (int, float)) or dur <= 0:
                        rejected.append(f'"{name}" skipped — invalid duration.')
                        continue
                    if pri not in ("high", "medium", "low"):
                        rejected.append(f'"{name}" skipped — invalid priority "{pri}".')
                        continue

                    # Check duplicate
                    duplicate = any(
                        t["title"] == name and not t.get("completed", False)
                        for t in st.session_state.tasks
                    )
                    if duplicate:
                        rejected.append(f'"{name}" already exists as an incomplete task.')
                        continue

                    if recur == "none":
                        recur = None
                    if recur and recur not in ("daily", "weekly"):
                        recur = None

                    st.session_state.tasks.append({
                        "title": name,
                        "duration_minutes": int(dur),
                        "priority": pri,
                        "recurrence": recur,
                        "completed": False,
                        "start_time": start if start else None,
                    })
                    added.append(name)

                if added:
                    st.success(result["message"])
                if rejected:
                    for r in rejected:
                        st.warning(r)

            elif result["action"] == "remove_task":
                removed = []
                not_found = []
                for task in result.get("tasks", []):
                    name = str(task.get("name", "")).strip()
                    idx = None
                    for i, t in enumerate(st.session_state.tasks):
                        if t["title"] == name:
                            idx = i
                            break
                    if idx is not None:
                        st.session_state.tasks.pop(idx)
                        removed.append(name)
                    else:
                        not_found.append(name)

                if removed:
                    st.success(result["message"])
                if not_found:
                    for n in not_found:
                        st.warning(f'Task "{n}" not found.')

            elif result["action"] == "complete_task":
                completed_names = []
                not_found = []
                for task in result.get("tasks", []):
                    name = str(task.get("name", "")).strip()
                    idx = find_task_idx(name, completed=False)
                    if idx is not None:
                        st.session_state.tasks[idx]["completed"] = True
                        completed_names.append(name)
                    else:
                        not_found.append(name)

                if completed_names:
                    st.success(result["message"])
                if not_found:
                    for n in not_found:
                        st.warning(f'Incomplete task "{n}" not found.')

            elif result["action"] == "edit_task":
                edited = []
                not_found = []
                for task in result.get("tasks", []):
                    original = str(task.get("original_name", "")).strip()
                    idx = None
                    for i, t in enumerate(st.session_state.tasks):
                        if t["title"] == original and not t.get("completed", False):
                            idx = i
                            break
                    if idx is None:
                        not_found.append(original)
                        continue

                    if task.get("name"):
                        st.session_state.tasks[idx]["title"] = str(task["name"]).strip()
                    if task.get("duration_minutes") and int(task["duration_minutes"]) > 0:
                        st.session_state.tasks[idx]["duration_minutes"] = int(task["duration_minutes"])
                    if task.get("priority") and str(task["priority"]).lower() in ("high", "medium", "low"):
                        st.session_state.tasks[idx]["priority"] = str(task["priority"]).lower()
                    if "recurrence" in task:
                        recur = task["recurrence"]
                        if recur == "none":
                            recur = None
                        st.session_state.tasks[idx]["recurrence"] = recur
                    if "start_time" in task:
                        st.session_state.tasks[idx]["start_time"] = task["start_time"]
                    edited.append(original)

                if edited:
                    st.success(result["message"])
                if not_found:
                    for n in not_found:
                        st.warning(f'Task "{n}" not found for editing.')
```

- [ ] **Step 3: Manually test in the browser**

Run: `python -m streamlit run app.py`

Test these scenarios:
1. Without `GOOGLE_API_KEY` set — verify the warning message appears.
2. With `GOOGLE_API_KEY` set — type "Add a 20-minute feeding task for Mochi at high priority" and click "Ask PawPal". Verify the task appears in the task list.
3. Type "What exercise does a dog need?" — verify an informational response appears.
4. Click "Ask PawPal" twice rapidly — verify the cooldown message appears.
5. Type "Remove Morning walk" — verify the task is removed.

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "feat: add AI Assistant section to Streamlit UI"
```

---

### Task 5: Add test for ask_assistant error handling

**Files:**
- Modify: `tests/test_ai_assistant.py`

- [ ] **Step 1: Write test for missing API key / bad response**

Append to `tests/test_ai_assistant.py`:

```python
def test_ask_assistant_handles_invalid_json(monkeypatch):
    """ask_assistant must return an error dict when Gemini returns non-JSON."""
    import time as _time_mod
    ai_assistant._last_request_ts = _time_mod.time() - ai_assistant.COOLDOWN_SECONDS - 1

    def fake_generate(self, contents, **kwargs):
        class FakeResponse:
            text = "This is not JSON at all"
        return FakeResponse()

    monkeypatch.setattr(
        "google.generativeai.GenerativeModel.generate_content",
        fake_generate,
    )

    result = ai_assistant.ask_assistant(
        user_message="hello",
        context="Owner: Jordan",
        api_key="fake-key",
    )

    assert result["action"] == "error"
    assert "trouble" in result["message"].lower()


def test_ask_assistant_handles_api_exception(monkeypatch):
    """ask_assistant must return an error dict when the API call raises."""
    import time as _time_mod
    ai_assistant._last_request_ts = _time_mod.time() - ai_assistant.COOLDOWN_SECONDS - 1

    def fake_generate(self, contents, **kwargs):
        raise RuntimeError("API quota exceeded")

    monkeypatch.setattr(
        "google.generativeai.GenerativeModel.generate_content",
        fake_generate,
    )

    result = ai_assistant.ask_assistant(
        user_message="hello",
        context="Owner: Jordan",
        api_key="fake-key",
    )

    assert result["action"] == "error"
    assert "error" in result["message"].lower()
```

- [ ] **Step 2: Run all ai_assistant tests**

Run: `python -m pytest tests/test_ai_assistant.py -v`
Expected: 7 passed

- [ ] **Step 3: Run existing pawpal tests to verify no regressions**

Run: `python -m pytest tests/test_pawpal.py -v`
Expected: 15 passed

- [ ] **Step 4: Commit**

```bash
git add tests/test_ai_assistant.py
git commit -m "test: add error handling tests for ask_assistant"
```

---

### Task 6: Update documentation

**Files:**
- Modify: `current_design.md`
- Modify: `README.md`

- [ ] **Step 1: Update current_design.md**

Add a new section after the existing "## UI Layer (app.py)" section:

```markdown

## AI Assistant Layer (ai_assistant.py)

`ai_assistant.py` is a pure-Python module with no Streamlit dependency. It wraps
the Gemini API to provide natural language interaction over the existing Scheduler.

- **`build_context()`** serializes the current PawPal state (owner, pet, tasks)
  into a text block injected into the Gemini prompt.
- **`ask_assistant()`** sends a single API call to Gemini with a system prompt
  that enforces structured JSON output. Returns a dict with `action`, `tasks`,
  and `message` fields.
- **Rate limiting:** a module-level timestamp enforces a 10-second cooldown
  between API calls.
- **Workflow:** User types a request → one Gemini call extracts intent into
  structured JSON → `app.py` validates the payload → valid changes are applied
  to `st.session_state.tasks` → friendly message is displayed. Gemini never
  mutates session state directly.

Supported actions: `add_task`, `remove_task`, `complete_task`, `edit_task`,
`generate_schedule`, `answer_question`.
```

Also add `ai_assistant.py` to the class diagram's module list. After the existing `Scheduler` class in the mermaid diagram, add:

```mermaid
    class AIAssistant {
        <<module>>
        +build_context(owner_name, pet_name, species, time_available, tasks) str
        +ask_assistant(user_message, context, api_key) dict
    }

    AIAssistant ..> Scheduler : "proposes actions validated by app.py"
```

- [ ] **Step 2: Update README.md**

In the Features section, add a bullet:

```markdown
- AI Assistant powered by Gemini: natural language task management, pet-care Q&A, schedule advice, and conflict explanations — all grounded in your current PawPal state.
```

In the "How It Works" section, add a new subsection:

```markdown
### AI Assistant

The AI Assistant uses Google's Gemini API as a natural language interface over the existing scheduler. When you type a request, a single API call converts it into a structured action (add task, remove task, edit task, etc.) with a friendly explanation. The app validates every suggestion before applying it — Gemini proposes, the Scheduler decides. A 10-second cooldown between requests prevents excessive API usage.
```

In the Setup section, add after the `pip install` step:

```markdown
Set your Gemini API key:

Create a `.env` file in the project root (or set the environment variable directly):

```bash
GOOGLE_API_KEY=your-api-key-here
```

Get a free API key at [Google AI Studio](https://aistudio.google.com/apikey).
```

In the "Using the App" section, add:

```markdown
8. Use the AI Assistant to add tasks in plain English, ask pet-care questions, or get schedule advice.
```

In the Project Structure, add `ai_assistant.py` and `tests/test_ai_assistant.py`.

In the File guide, add:

```markdown
- `ai_assistant.py`: Gemini API wrapper for natural language interaction.
- `tests/test_ai_assistant.py`: tests for context building, rate limiting, and error handling.
```

- [ ] **Step 3: Commit**

```bash
git add current_design.md README.md
git commit -m "docs: add AI Assistant to design docs and README"
```

---

### Task 7: Final verification

- [ ] **Step 1: Run full test suite**

Run: `python -m pytest tests/ -v`
Expected: All tests pass (15 pawpal + 7 ai_assistant = 22 total).

- [ ] **Step 2: Run the app end-to-end**

Run: `GOOGLE_API_KEY=your-key python -m streamlit run app.py`

Verify:
1. AI Assistant section appears at the bottom
2. "Add a 30-minute walk" → task appears in task list
3. "What should I feed a dog?" → informational answer appears
4. Rapid double-click → cooldown warning
5. "Generate schedule" button still works normally
6. Existing task management (add/done/remove) still works

- [ ] **Step 3: Final commit if any fixups needed**

```bash
git add -A
git commit -m "fix: final polish for AI assistant integration"
```
