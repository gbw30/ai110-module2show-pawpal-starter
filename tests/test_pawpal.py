# NOTE: Task completion test not implemented.
# The original test spec called for testing mark_complete() changing a task's status.
# This was not implemented because Task has no status attribute or mark_complete() method
# in the current design. The MVP scope (per README) is planning and scheduling, not
# tracking whether tasks were completed. Adding completion state would require changes
# to the UML, pawpal_system.py, and the Streamlit UI — beyond the current iteration.

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
