# AI Reliability Evaluation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an integrated AI Reliability Evaluation feature so PawPal+ clearly satisfies the "Reliability or Testing System" advanced AI guideline. The app should measure whether the AI Assistant returns correct structured actions, avoids unnecessary Gemini calls, and handles quota/errors safely.

**Architecture:** Add a pure-Python `ai_reliability.py` module that runs deterministic assistant evaluation cases. `app.py` exposes the results inside the main AI Assistant section. The default evaluation must not call Gemini, preserving free-tier quota. An optional live Gemini smoke check may run only when explicitly enabled.

**Tech Stack:** Python 3.10+, Streamlit, pytest, existing `ai_assistant.py`, existing `pawpal_system.py`.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `ai_reliability.py` | Create | Evaluation harness for assistant reliability checks |
| `tests/test_ai_reliability.py` | Create | Unit tests for scoring, failure reporting, and no-API local eval behavior |
| `app.py` | Modify | Add integrated "AI Reliability Check" UI in the AI Assistant section |
| `README.md` | Modify | Document the advanced AI reliability feature and usage |
| `current_design.md` | Modify | Add reliability/evaluation layer to design notes |

---

### Task 1: Create AI reliability evaluation harness

**Files:**
- Create: `ai_reliability.py`
- Create: `tests/test_ai_reliability.py`

- [ ] **Step 1: Write failing tests for the evaluation API**

Create tests for:

- `run_reliability_checks(...)` returns a summary dict.
- Local add-task prompt passes with expected `action == "add_task"`.
- Local complete-task prompt passes with expected `action == "complete_task"`.
- Local remove-task prompt passes with expected `action == "remove_task"`.
- Results include `total`, `passed`, `failed`, `pass_rate`, and per-case details.
- Default evaluation does not call Gemini.

- [ ] **Step 2: Implement `ai_reliability.py`**

Add this public API:

```python
def run_reliability_checks(
    context: str,
    tasks: list[dict],
    api_key: str = "",
    include_live_gemini: bool = False,
) -> dict:
    ...
```

Return shape:

```python
{
    "total": 4,
    "passed": 4,
    "failed": 0,
    "pass_rate": 1.0,
    "results": [
        {
            "name": "local_add_daily_walk",
            "prompt": "...",
            "passed": True,
            "expected_action": "add_task",
            "actual_action": "add_task",
            "message": "..."
        }
    ]
}
```

Default cases aligned to current assistant capabilities:

- Add task: `Add a daily 20 minute morning walk for Mochi at 8am high priority`
- Natural add phrase: `I need to brush Mochi for 15 minutes weekly`
- Complete task: `Mark morning walk done`
- Remove task: `Remove morning walk`
- List tasks: `Show my tasks`
- Schedule guidance: `Generate a schedule for today`
- Missing-key guardrail: `How often should a dog drink water?`

- [ ] **Step 3: Add optional live Gemini smoke check**

If `include_live_gemini=True`, run one minimal Gemini-backed prompt that should return `answer_question`.

If Gemini returns 429 or another API error, mark only the live check as failed and include the existing safe error message. Do not fail the local deterministic cases because of Gemini quota.

- [ ] **Step 4: Run tests**

```bash
.\.venv\Scripts\python.exe -m pytest tests/test_ai_reliability.py -v
```

Expected: all reliability tests pass.

---

### Task 2: Integrate reliability check into Streamlit app

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Import the evaluation function**

Import `run_reliability_checks` near the existing AI assistant imports.

- [ ] **Step 2: Add UI inside the AI Assistant section**

Add an expander below the Ask PawPal controls:

```text
AI Reliability Check
```

Inside the expander:

- Button: `Run reliability check`
- Checkbox: `Include one live Gemini smoke test` default `False`
- Metrics:
  - Total checks
  - Passed
  - Pass rate
- Table of case results

- [ ] **Step 3: Keep default behavior free-tier friendly**

The default reliability check must run without Gemini API usage. Only the optional live smoke test may call Gemini.

- [ ] **Step 4: Display failures clearly**

If any case fails, show `st.warning` with failed case names. If all pass, show `st.success`.

---

### Task 3: Document rubric alignment

**Files:**
- Modify: `README.md`
- Modify: `current_design.md`

- [ ] **Step 1: Update README features**

Add a feature bullet:

```text
AI Reliability Evaluation: built-in checks verify that the AI Assistant returns correct structured actions, avoids unnecessary Gemini calls, and handles quota errors safely.
```

- [ ] **Step 2: Update README testing section**

Update the test count and include `tests/test_ai_reliability.py`.

Document that the project satisfies the advanced AI guideline through a **Reliability or Testing System** integrated into the main app.

- [ ] **Step 3: Update design docs**

Add an "AI Reliability Layer" section explaining:

- `ai_reliability.py` runs deterministic assistant evaluations.
- `app.py` exposes the reliability check in the main UI.
- Local checks preserve Gemini free-tier quota.
- Optional live Gemini check validates the API-backed path when quota is available.

---

### Task 4: Final verification

**Files:**
- All changed files

- [ ] **Step 1: Run full test suite**

```bash
.\.venv\Scripts\python.exe -m pytest tests/ -v
```

Expected: all existing scheduler, assistant, and reliability tests pass.

- [ ] **Step 2: Manual Streamlit verification**

Run:

```bash
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Verify:

- AI Assistant still adds local tasks without Gemini.
- Reliability Check appears in the main app.
- Default reliability check runs without API quota.
- Results show pass rate and case details.
- Optional live Gemini smoke test handles 429 safely.

- [ ] **Step 3: Commit**

```bash
git add ai_reliability.py tests/test_ai_reliability.py app.py README.md current_design.md
git commit -m "feat: add AI reliability evaluation system"
```

---

## Acceptance Criteria

- The project has an integrated reliability/testing feature visible in the Streamlit app.
- The reliability feature meaningfully evaluates the AI Assistant's structured behavior.
- Default checks do not consume Gemini quota.
- Optional live Gemini check is explicit and safe.
- Full test suite passes.
- README clearly explains how this satisfies the advanced AI guideline.
