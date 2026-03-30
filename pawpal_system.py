from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, time, timedelta
from itertools import combinations
from typing import Literal


RecurrenceType = Literal["daily", "weekly"] | None


@dataclass
class Owner:
    name: str
    time_available: int  # minutes per day


@dataclass
class Pet:
    name: str
    species: str


@dataclass
class Task:
    name: str
    duration: int                       # minutes
    priority: int                       # 1 = high, 2 = medium, 3 = low
    completed: bool = False
    recurrence: RecurrenceType = None
    due_date: date | None = None
    start_time: time | None = None      # wall-clock start time for conflict detection

    def set_name(self, name: str) -> None:
        """Update the task's name."""
        self.name = name

    def set_duration(self, minutes: int) -> None:
        """Update the task's duration in minutes."""
        self.duration = minutes

    def set_priority(self, priority: int) -> None:
        """Update the task's priority (1 = high, 2 = medium, 3 = low)."""
        self.priority = priority

    def mark_complete(self) -> None:
        """Mark the task as completed."""
        self.completed = True

    def next_occurrence(self) -> Task | None:
        """Return a new Task for the next recurrence, or None if not recurring."""
        deltas = {"daily": timedelta(days=1), "weekly": timedelta(weeks=1)}
        delta = deltas.get(self.recurrence)
        if delta is None:
            return None
        return Task(
            name=self.name,
            duration=self.duration,
            priority=self.priority,
            recurrence=self.recurrence,
            due_date=date.today() + delta,
        )

    def __str__(self) -> str:
        """Return a human-readable summary of the task."""
        priority_label = {1: "High", 2: "Medium", 3: "Low"}.get(self.priority, "Unknown")
        status = "[Done] " if self.completed else ""
        recurrence = f", {self.recurrence}" if self.recurrence else ""
        due = f", due {self.due_date}" if self.due_date else ""
        start = f", starts {self.start_time.strftime('%H:%M')}" if self.start_time else ""
        return f"{status}{self.name} ({self.duration} min, {priority_label} priority{recurrence}{due}{start})"


@dataclass
class Scheduler:
    owner: Owner
    pet: Pet
    tasks: list[Task] = field(default_factory=list)
    planned_tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> bool:
        """Add a task if no incomplete task with the same name exists. Returns True if added."""
        name_taken = any(t.name == task.name and not t.completed for t in self.tasks)
        if name_taken:
            return False
        self.tasks.append(task)
        return True

    def remove_task(self, task: Task) -> None:
        """Remove a task from the pool by name, avoiding object identity fragility."""
        self.tasks = [t for t in self.tasks if t.name != task.name]

    def edit_task(self, task: Task, name: str, duration: int, priority: int) -> None:
        """Find a task by its current name and update its fields in place."""
        for t in self.tasks:
            if t.name == task.name:
                t.set_name(name)
                t.set_duration(duration)
                t.set_priority(priority)
                break

    def complete_task(self, task: Task) -> None:
        """Mark a task complete and schedule its next occurrence if it is recurring."""
        task.mark_complete()
        next_task = task.next_occurrence()
        if next_task is not None:
            self.add_task(next_task)

    def sort_by_time(self) -> list[Task]:
        """Sort the task pool by duration (shortest first) in place and return it."""
        self.tasks.sort(key=lambda t: t.duration)
        return self.tasks

    def filter_tasks(
        self,
        completed: bool | None = None,
        pet_name: str | None = None,
    ) -> list[Task]:
        """Return tasks matching the given completion status and/or pet name."""
        if pet_name is not None and self.pet.name != pet_name:
            return []
        result = self.tasks
        if completed is not None:
            result = [t for t in result if t.completed == completed]
        return result

    def detect_conflicts(self, other: Scheduler | None = None) -> list[str]:
        """Check for tasks whose time windows overlap and return a warning string for each pair.

        Only tasks with a start_time set are considered. Completed tasks are ignored.
        Pass another Scheduler via `other` to also detect cross-pet conflicts —
        useful when one owner manages multiple pets whose tasks share the same time slot.
        Returns an empty list when no conflicts are found. Never raises.
        """

        def to_minutes(t: time) -> int:
            """Convert a time object to total minutes since midnight for arithmetic comparisons."""
            return t.hour * 60 + t.minute

        def fmt(minutes: int) -> str:
            """Format a minute count back to a HH:MM string for display in warning messages."""
            return f"{minutes // 60:02d}:{minutes % 60:02d}"

        candidates = [
            (t, self.pet.name)
            for t in self.tasks
            if t.start_time is not None and not t.completed
        ]
        if other is not None:
            candidates += [
                (t, other.pet.name)
                for t in other.tasks
                if t.start_time is not None and not t.completed
            ]

        def overlaps(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
            """Return True if two time windows [a_start, a_end) and [b_start, b_end) overlap."""
            return a_start < b_end and b_start < a_end

        warnings = []
        for (task_a, pet_a), (task_b, pet_b) in combinations(candidates, 2):
            a_start = to_minutes(task_a.start_time)
            a_end   = a_start + task_a.duration
            b_start = to_minutes(task_b.start_time)
            b_end   = b_start + task_b.duration
            if overlaps(a_start, a_end, b_start, b_end):
                warnings.append(
                    f"  CONFLICT: [{pet_a}] \"{task_a.name}\" "
                    f"({task_a.start_time.strftime('%H:%M')} to {fmt(a_end)}) "
                    f"overlaps [{pet_b}] \"{task_b.name}\" "
                    f"({task_b.start_time.strftime('%H:%M')} to {fmt(b_end)})"
                )
        return warnings

    def generate_plan(self) -> list[Task]:
        """Build a daily plan using a greedy priority-first algorithm.

        Steps:
          1. Filter out completed tasks.
          2. Sort remaining tasks by priority (1 = highest), breaking ties by shortest duration first.
          3. Greedily accept each task if it fits within the owner's available time.

        The result is stored in `planned_tasks` for use by `explain_plan()` and returned.
        Tasks that exceed the remaining time budget are skipped and will appear as excluded
        in the plan explanation.
        """
        # Step 1: only consider tasks that haven't been done yet
        incomplete = [t for t in self.tasks if not t.completed]

        # Step 2: highest priority first; shortest duration wins ties
        by_priority_then_shortest = lambda t: (t.priority, t.duration)
        sorted_tasks = sorted(incomplete, key=by_priority_then_shortest)

        # Step 3: greedily fill available time
        plan = []
        time_used = 0
        for task in sorted_tasks:
            if time_used + task.duration <= self.owner.time_available:
                plan.append(task)
                time_used += task.duration

        self.planned_tasks = plan
        return self.planned_tasks

    def explain_plan(self) -> str:
        """Return a plain-text summary of the plan, including excluded tasks and time usage."""
        if not self.planned_tasks:
            return "No plan generated yet. Run generate_plan() first."

        planned_names = {t.name for t in self.planned_tasks}
        excluded = [t for t in self.tasks if t.name not in planned_names and not t.completed]
        time_used = sum(t.duration for t in self.planned_tasks)
        remaining = self.owner.time_available - time_used

        lines = [
            f"Daily care plan for {self.pet.name} ({self.pet.species})",
            f"Owner: {self.owner.name} - Available: {self.owner.time_available} min | Used: {time_used} min | Remaining: {remaining} min",
            "",
            "Scheduled tasks (highest priority first):",
        ]
        for task in self.planned_tasks:
            lines.append(f"  - {task}")

        if excluded:
            lines.append("")
            lines.append("Excluded tasks (not enough time remaining):")
            for task in excluded:
                lines.append(f"  - {task}")

        return "\n".join(lines)
