# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Smarter Scheduling

PawPal+ goes beyond a simple task list with several scheduling improvements:

- **Priority-first greedy planning** — `generate_plan()` sorts tasks by priority (high → low),
  breaking ties by shortest duration first, then fills the owner's available time greedily.
  High-priority tasks such as feeding and medication are always considered before lower-priority ones.

- **Recurring tasks** — Tasks can be marked `daily` or `weekly`. When completed via
  `complete_task()`, a new instance is automatically created with the correct next due date
  using `timedelta` (`+1 day` for daily, `+7 days` for weekly).

- **Conflict detection** — `detect_conflicts()` checks whether any two tasks have overlapping
  time windows using an interval overlap algorithm. Pass a second `Scheduler` to catch
  cross-pet conflicts — for example, two pets both scheduled for feeding at the same time.

- **Duplicate prevention** — `add_task()` blocks adding a task whose name already exists
  in the pool as an incomplete task, preventing accidental duplicates while still allowing
  recurrence instances once the previous task is marked done.

- **Filtering and sorting** — `filter_tasks()` returns tasks by completion status or pet name.
  `sort_by_time()` reorders the pool by duration (shortest first) for quick review.

## Testing PawPal+

### Running the tests

```bash
python -m pytest tests/test_pawpal.py -v
```

The `-v` flag prints each test name and its pass/fail result. All 15 tests should pass.

### What the tests cover

The suite verifies four areas of the scheduling system:

- **Priority ordering** — `generate_plan()` sorts tasks correctly by priority and breaks ties by shortest duration first.
- **Recurrence logic** — completing a daily or weekly task spawns a new instance with the correct due date; completing a non-recurring task does not.
- **Conflict detection** — overlapping time windows are flagged; back-to-back tasks and cross-pet conflicts are handled correctly.
- **Duplicate prevention and filtering** — `add_task()` blocks duplicate incomplete tasks but allows re-entry after completion; `filter_tasks()` returns an empty list for an unrecognized pet name.

### Test logic in depth

#### Setup

`make_scheduler(time_available=60)` is a shared helper that returns a `Scheduler` with a default owner (Jordan, 60 min) and pet (Mochi, dog). Every test that needs a scheduler calls this to avoid repeating setup code.

---

#### Original tests

**`test_task_addition_increases_count`**
Calls `add_task()` twice with different task names and asserts the pool grows from 0 → 1 → 2. Verifies the most basic contract: tasks are actually stored.

**`test_generate_plan_respects_time_available`**
Owner has 40 minutes. Adds a 30-min task, a 10-min task, and a 45-min task. Asserts the plan's total duration never exceeds 40 and that `Bath` (45 min) exists in the pool but is absent from the plan.

---

#### Priority ordering

**`test_generate_plan_orders_by_priority`**
Adds three tasks in reverse priority order (low, high, medium) and checks the plan returns them in correct order: Feeding (1) → Enrichment (2) → Grooming (3). Verifies that input order does not affect output — only priority does.

**`test_generate_plan_tiebreaks_by_shortest_duration`**
All three tasks share priority 2 but have durations of 30, 10, and 20 minutes. Asserts the plan's durations are sorted ascending. Verifies the tie-breaking rule: equal-priority tasks are ordered shortest first.

**`test_generate_plan_exact_fit_is_included`**
Owner has exactly 30 minutes; task is exactly 30 minutes. Asserts the task is scheduled. Verifies the greedy condition uses `<=` so an exact fit is never accidentally excluded.

**`test_generate_plan_skips_completed_tasks`**
Adds a task, marks it complete, then generates a plan. Asserts the plan is empty. Verifies completed tasks are filtered out before scheduling runs.

---

#### Recurring tasks

**`test_complete_daily_task_spawns_next_occurrence`**
Creates a `recurrence="daily"` task and calls `complete_task()`. Checks that exactly one incomplete task remains and its `due_date` equals `today + 1 day`. Verifies daily recurrence spawning.

**`test_complete_weekly_task_spawns_next_occurrence`**
Same structure with `recurrence="weekly"`. Asserts `due_date` equals `today + 7 days`. Verifies weekly recurrence spawning.

**`test_complete_nonrecurring_task_spawns_nothing`**
No `recurrence` set. Calls `complete_task()` and asserts the task count stays at 1. Verifies no extra task is created for one-time tasks.

---

#### Duplicate prevention

**`test_add_task_blocks_duplicate_incomplete`**
Adds `"Feeding"` twice. Asserts `add_task()` returns `False` on the second call and the pool still holds only one task. Verifies the duplicate guard works.

**`test_add_task_allows_same_name_after_completion`**
Adds `"Feeding"`, marks it complete, then adds `"Feeding"` again. Asserts `add_task()` returns `True` and one incomplete task exists. Verifies that completion unlocks the name so recurring tasks can re-enter the pool.

---

#### Conflict detection

**`test_detect_conflicts_flags_overlapping_tasks`**
Morning walk starts 08:00 and runs 30 minutes (ends 08:30). Enrichment starts 08:15 — a 15-minute overlap. Asserts exactly one conflict warning is returned.

**`test_detect_conflicts_ignores_back_to_back`**
Feeding ends at 07:10 and Morning walk starts at 07:10. Asserts zero warnings. Verifies the overlap formula uses strict inequalities so touching endpoints are not treated as a conflict.

**`test_detect_conflicts_cross_pet`**
Two schedulers (Mochi and Luna) each have a `"Feeding"` task starting at 09:00. Passes `luna_scheduler` as `other=`. Asserts one conflict warning is generated. Verifies that cross-pet overlaps are caught when a second scheduler is provided.

---

#### Filtering

**`test_filter_tasks_wrong_pet_name_returns_empty`**
The scheduler belongs to Mochi. Calls `filter_tasks(pet_name="Luna")` and asserts the result is `[]`. Verifies the pet name guard returns an empty list rather than raising an error or leaking another pet's tasks.

---

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.
