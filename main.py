from pawpal_system import Owner, Pet, Task, Scheduler

# --- Setup ---
owner = Owner(name="Jordan", time_available=60)

mochi = Pet(name="Mochi", species="dog")
luna = Pet(name="Luna", species="cat")

# --- Tasks for Mochi ---
mochi_scheduler = Scheduler(owner=owner, pet=mochi)
mochi_scheduler.add_task(Task(name="Morning walk",   duration=30, priority=1))
mochi_scheduler.add_task(Task(name="Feeding",        duration=10, priority=1))
mochi_scheduler.add_task(Task(name="Bath",           duration=45, priority=3))

# --- Tasks for Luna ---
luna_scheduler = Scheduler(owner=owner, pet=luna)
luna_scheduler.add_task(Task(name="Feeding",         duration=5,  priority=1))
luna_scheduler.add_task(Task(name="Playtime",        duration=20, priority=2))
luna_scheduler.add_task(Task(name="Vet checkup",     duration=60, priority=3))

# --- Generate and print schedules ---
print("=" * 50)
print("TODAY'S SCHEDULE")
print("=" * 50)

for scheduler in [mochi_scheduler, luna_scheduler]:
    scheduler.generate_plan()
    print()
    print(scheduler.explain_plan())
    print("-" * 50)
