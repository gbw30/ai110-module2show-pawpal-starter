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

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.
