from datetime import time
from pawpal_system import Owner, Pet, Task, Scheduler


def make_scheduler(time_available: int = 60) -> Scheduler:
    """Create a minimal Scheduler with a default owner and pet for use in tests."""
    return Scheduler(
        owner=Owner(name="Jordan", time_available=time_available),
        pet=Pet(name="Mochi", species="dog"),
    )


def test_task_addition_increases_count():
    """Verify that add_task() increases the Scheduler's task count by one per call."""
    scheduler = make_scheduler()
    assert len(scheduler.tasks) == 0

    scheduler.add_task(Task(name="Morning walk", duration=30, priority=1))
    assert len(scheduler.tasks) == 1

    scheduler.add_task(Task(name="Feeding", duration=10, priority=1))
    assert len(scheduler.tasks) == 2


def test_generate_plan_respects_time_available():
    """Verify that generate_plan() excludes tasks that would exceed the owner's available time."""
    scheduler = make_scheduler(time_available=40)
    scheduler.add_task(Task(name="Morning walk", duration=30, priority=1))
    scheduler.add_task(Task(name="Feeding",      duration=10, priority=1))
    scheduler.add_task(Task(name="Bath",         duration=45, priority=2))

    plan = scheduler.generate_plan()
    total_duration = sum(t.duration for t in plan)

    assert total_duration <= 40
    assert any(t.name == "Bath" for t in scheduler.tasks)   # task exists in pool
    assert all(t.name != "Bath" for t in plan)              # but excluded from plan


# --- Priority ordering ---

def test_generate_plan_orders_by_priority():
    """High-priority tasks must appear before low-priority tasks in the plan."""
    scheduler = make_scheduler(time_available=60)
    scheduler.add_task(Task(name="Grooming",      duration=15, priority=3))  # low
    scheduler.add_task(Task(name="Feeding",       duration=10, priority=1))  # high
    scheduler.add_task(Task(name="Enrichment",    duration=15, priority=2))  # medium

    plan = scheduler.generate_plan()
    names = [t.name for t in plan]

    assert names.index("Feeding") < names.index("Enrichment")
    assert names.index("Enrichment") < names.index("Grooming")


def test_generate_plan_tiebreaks_by_shortest_duration():
    """Equal-priority tasks must be ordered shortest-first."""
    scheduler = make_scheduler(time_available=60)
    scheduler.add_task(Task(name="Long walk",   duration=30, priority=2))
    scheduler.add_task(Task(name="Short play",  duration=10, priority=2))
    scheduler.add_task(Task(name="Medium groom", duration=20, priority=2))

    plan = scheduler.generate_plan()
    durations = [t.duration for t in plan]

    assert durations == sorted(durations)


def test_generate_plan_exact_fit_is_included():
    """A task whose duration exactly equals the remaining time must be scheduled."""
    scheduler = make_scheduler(time_available=30)
    scheduler.add_task(Task(name="Morning walk", duration=30, priority=1))

    plan = scheduler.generate_plan()

    assert len(plan) == 1
    assert plan[0].name == "Morning walk"


def test_generate_plan_skips_completed_tasks():
    """Completed tasks must not appear in a newly generated plan."""
    scheduler = make_scheduler(time_available=60)
    task = Task(name="Feeding", duration=10, priority=1)
    scheduler.add_task(task)
    task.mark_complete()

    plan = scheduler.generate_plan()

    assert len(plan) == 0


# --- Recurring tasks ---

def test_complete_daily_task_spawns_next_occurrence():
    """Completing a daily task must add a new task due tomorrow."""
    from datetime import date
    scheduler = make_scheduler()
    task = Task(name="Feeding", duration=10, priority=1, recurrence="daily")
    scheduler.add_task(task)

    scheduler.complete_task(task)

    incomplete = [t for t in scheduler.tasks if not t.completed]
    assert len(incomplete) == 1
    assert incomplete[0].due_date == date.today() + __import__("datetime").timedelta(days=1)


def test_complete_weekly_task_spawns_next_occurrence():
    """Completing a weekly task must add a new task due in 7 days."""
    from datetime import date, timedelta
    scheduler = make_scheduler()
    task = Task(name="Bath", duration=20, priority=2, recurrence="weekly")
    scheduler.add_task(task)

    scheduler.complete_task(task)

    incomplete = [t for t in scheduler.tasks if not t.completed]
    assert len(incomplete) == 1
    assert incomplete[0].due_date == date.today() + timedelta(weeks=1)


def test_complete_nonrecurring_task_spawns_nothing():
    """Completing a non-recurring task must not add any new tasks."""
    scheduler = make_scheduler()
    task = Task(name="One-time vet visit", duration=60, priority=1)
    scheduler.add_task(task)

    scheduler.complete_task(task)

    assert len(scheduler.tasks) == 1  # only the original, now completed


# --- Duplicate prevention ---

def test_add_task_blocks_duplicate_incomplete():
    """add_task() must reject a task whose name matches an existing incomplete task."""
    scheduler = make_scheduler()
    scheduler.add_task(Task(name="Feeding", duration=10, priority=1))

    added = scheduler.add_task(Task(name="Feeding", duration=10, priority=1))

    assert added is False
    assert len(scheduler.tasks) == 1


def test_add_task_allows_same_name_after_completion():
    """After a task is completed, a new task with the same name must be accepted."""
    scheduler = make_scheduler()
    task = Task(name="Feeding", duration=10, priority=1)
    scheduler.add_task(task)
    task.mark_complete()

    added = scheduler.add_task(Task(name="Feeding", duration=10, priority=1))

    assert added is True
    incomplete = [t for t in scheduler.tasks if not t.completed]
    assert len(incomplete) == 1


# --- Conflict detection ---

def test_detect_conflicts_flags_overlapping_tasks():
    """Two tasks whose time windows overlap must produce a conflict warning."""
    scheduler = make_scheduler()
    scheduler.add_task(Task(name="Morning walk", duration=30, priority=1, start_time=time(8, 0)))
    scheduler.add_task(Task(name="Enrichment",   duration=15, priority=2, start_time=time(8, 15)))

    warnings = scheduler.detect_conflicts()

    assert len(warnings) == 1


def test_detect_conflicts_ignores_back_to_back():
    """Tasks that end exactly when the next starts must NOT be flagged."""
    scheduler = make_scheduler()
    scheduler.add_task(Task(name="Feeding",      duration=10, priority=1, start_time=time(7, 0)))
    scheduler.add_task(Task(name="Morning walk", duration=30, priority=1, start_time=time(7, 10)))

    warnings = scheduler.detect_conflicts()

    assert len(warnings) == 0


def test_detect_conflicts_cross_pet():
    """Two schedulers with tasks at the same time must flag a conflict when other= is passed."""
    owner = Owner(name="Jordan", time_available=90)
    mochi_scheduler = Scheduler(owner=owner, pet=Pet(name="Mochi", species="dog"))
    luna_scheduler  = Scheduler(owner=owner, pet=Pet(name="Luna",  species="cat"))

    mochi_scheduler.add_task(Task(name="Feeding", duration=10, priority=1, start_time=time(9, 0)))
    luna_scheduler.add_task( Task(name="Feeding", duration=5,  priority=1, start_time=time(9, 0)))

    warnings = mochi_scheduler.detect_conflicts(other=luna_scheduler)

    assert len(warnings) == 1


# --- Filtering ---

def test_filter_tasks_wrong_pet_name_returns_empty():
    """filter_tasks() with a pet name that doesn't match must return an empty list."""
    scheduler = make_scheduler()
    scheduler.add_task(Task(name="Feeding", duration=10, priority=1))

    result = scheduler.filter_tasks(pet_name="Luna")

    assert result == []
