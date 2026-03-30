from dataclasses import dataclass, field


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
    duration: int   # minutes
    priority: int   # 1 = high, 2 = medium, 3 = low

    def set_name(self, name: str) -> None:
        """Update the task's name."""
        self.name = name

    def set_duration(self, minutes: int) -> None:
        """Update the task's duration in minutes."""
        self.duration = minutes

    def set_priority(self, priority: int) -> None:
        """Update the task's priority (1 = high, 2 = medium, 3 = low)."""
        self.priority = priority

    def __str__(self) -> str:
        """Return a human-readable summary of the task for display and plan output."""
        priority_label = {1: "High", 2: "Medium", 3: "Low"}.get(self.priority, "Unknown")
        return f"{self.name} ({self.duration} min, {priority_label} priority)"


@dataclass
class Scheduler:
    owner: Owner
    pet: Pet
    tasks: list[Task] = field(default_factory=list)
    planned_tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Append a task to the pool of available tasks."""
        self.tasks.append(task)

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

    def generate_plan(self) -> list[Task]:
        """Sort tasks by priority and greedily select those that fit within available time."""
        sorted_tasks = sorted(self.tasks, key=lambda t: t.priority)
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
        excluded = [t for t in self.tasks if t.name not in planned_names]
        time_used = sum(t.duration for t in self.planned_tasks)

        lines = [
            f"Daily care plan for {self.pet.name} ({self.pet.species})",
            f"Owner: {self.owner.name} — Available: {self.owner.time_available} min | Used: {time_used} min | Remaining: {self.owner.time_available - time_used} min",
            "",
            "Scheduled tasks (highest priority first):",
        ]
        for task in self.planned_tasks:
            lines.append(f"  • {task}")

        if excluded:
            lines.append("")
            lines.append("Excluded tasks (not enough time remaining):")
            for task in excluded:
                lines.append(f"  • {task}")

        return "\n".join(lines)
