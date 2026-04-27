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
