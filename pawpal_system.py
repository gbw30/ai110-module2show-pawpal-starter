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
        self.name = name

    def set_duration(self, minutes: int) -> None:
        self.duration = minutes

    def set_priority(self, priority: int) -> None:
        self.priority = priority

    def __str__(self) -> str:
        priority_label = {1: "High", 2: "Medium", 3: "Low"}.get(self.priority, "Unknown")
        return f"{self.name} ({self.duration} min, {priority_label} priority)"


@dataclass
class Scheduler:
    owner: Owner
    pet: Pet
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        pass

    def remove_task(self, task: Task) -> None:
        pass

    def edit_task(self, task: Task, name: str, duration: int, priority: int) -> None:
        pass

    def generate_plan(self) -> list[Task]:
        pass

    def explain_plan(self) -> str:
        pass
