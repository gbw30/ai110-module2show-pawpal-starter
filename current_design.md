# PawPal+ Current System Design

## Class Diagram

```mermaid
classDiagram
    class Owner {
        +String name
        +int time_available
        +__init__(name: str, time_available: int)
    }

    class Pet {
        +String name
        +String species
        +__init__(name: str, species: str)
    }

    class Task {
        +String name
        +int duration
        +int priority
        +bool completed
        +RecurrenceType recurrence
        +date|None due_date
        +time|None start_time
        +__init__(name, duration, priority, completed, recurrence, due_date, start_time)
        +set_name(name: str)
        +set_duration(minutes: int)
        +set_priority(priority: int)
        +mark_complete()
        +next_occurrence() Task|None
        +__str__() str
    }

    class Scheduler {
        +Owner owner
        +Pet pet
        +list tasks
        +list planned_tasks
        +add_task(task: Task) bool
        +remove_task(task: Task)
        +edit_task(task: Task, name: str, duration: int, priority: int)
        +complete_task(task: Task)
        +sort_by_time() list
        +filter_tasks(completed, pet_name) list
        +detect_conflicts(other: Scheduler|None) list
        +generate_plan() list
        +explain_plan() str
    }

    Scheduler "1" --> "1" Owner : uses
    Scheduler "1" --> "1" Pet : uses
    Scheduler "1" --> "0..*" Task : manages
    complete_task ..> next_occurrence : calls
    next_occurrence ..> add_task : spawns via
    generate_plan ..> planned_tasks : writes to
    explain_plan ..> planned_tasks : reads from
    detect_conflicts ..> Task : reads start_time
```

## Design Notes

- Architecture upgraded from MVP to full product.
- `RecurrenceType` is `Literal["daily", "weekly"] | None`. Daily tasks recur
  `today + 1 day`, weekly tasks recur `today + 7 days` using `timedelta`.
- `Task.next_occurrence()` is responsible for producing the next Task instance.
  `Scheduler.complete_task()` calls it and adds the result — keeping recurrence
  logic in Task and lifecycle coordination in Scheduler.
- `add_task()` duplicate check was updated: it blocks a new task only if an
  **incomplete** task with the same name already exists, allowing recurrence
  instances to be added after the previous one is completed.
- `generate_plan()` filters out completed tasks before scheduling.
- `planned_tasks` stores the output of `generate_plan()` so `explain_plan()`
  reads a stable snapshot without re-running scheduling logic.
- `filter_tasks()` accepts `completed` and/or `pet_name`; either can be omitted.
- `sort_by_time()` sorts `self.tasks` in place by duration (shortest first).
- `Task.start_time` is an optional `datetime.time` used exclusively by
  `detect_conflicts()`. Tasks without a start time are ignored by conflict checks.
- `detect_conflicts(other=None)` uses an interval overlap formula
  (`a_start < b_end and b_start < a_end`) with `itertools.combinations` to check
  all task pairs. Passing a second `Scheduler` via `other` extends the check across
  two pets (cross-pet conflict detection).

## UI Layer (app.py)

`app.py` is the Streamlit frontend. It stores tasks as plain dicts in
`st.session_state` and converts them to `Task` objects only when needed via
`build_scheduler()`. Key UI components:

- **`st.metric`** — task count summary (Total / Incomplete / Completed) and schedule
  time budget (Available / Scheduled / Remaining).
- **`st.tabs`** — separates the read-only Overview (`st.dataframe`) from the
  interactive Manage Tasks view (Done / Remove buttons).
- **`st.dataframe`** — renders filtered/sorted task lists and the generated schedule
  as structured tables.
- **`st.success` / `st.warning` / `st.error`** — conflict alerts, schedule status,
  and excluded-task notices use the appropriate severity level.
- Recurrence spawning is handled in the UI's Done button handler: when a recurring
  task is marked complete, a new task dict with the correct `due_date` is appended
  to `st.session_state.tasks` before `st.rerun()`.
