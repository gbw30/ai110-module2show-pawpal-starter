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
        +__init__(name: str, duration: int, priority: int)
        +set_name(name: str)
        +set_duration(minutes: int)
        +set_priority(priority: int)
        +__str__() str
    }

    class Scheduler {
        +Owner owner
        +Pet pet
        +list tasks
        +list planned_tasks
        +add_task(task: Task)
        +remove_task(task: Task)
        +edit_task(task: Task, name: str, duration: int, priority: int)
        +generate_plan() list
        +explain_plan() str
    }

    Scheduler "1" --> "1" Owner : uses
    Scheduler "1" --> "1" Pet : uses
    Scheduler "1" --> "0..*" Task : manages
    generate_plan ..> planned_tasks : writes to
    explain_plan ..> planned_tasks : reads from
```

## Design Notes

- `planned_tasks` was added to `Scheduler` after the initial skeleton review.
  It stores the output of `generate_plan()` so that `explain_plan()` has a stable
  reference without needing to re-run scheduling logic.
- `Owner` and `Pet` use constructor-only initialization — no setters needed since
  they are data containers set once via the UI form.
- `Task` retains setters to support the edit task flow after creation.
- `remove_task()` and `edit_task()` match by task name, not object identity,
  to avoid fragile reference comparisons in Streamlit's session state.
