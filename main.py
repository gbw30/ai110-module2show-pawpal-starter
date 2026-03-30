from datetime import time
from pawpal_system import Owner, Pet, Task, Scheduler

# --- Setup ---
owner = Owner(name="Jordan", time_available=90)
mochi = Pet(name="Mochi", species="dog")
luna  = Pet(name="Luna",  species="cat")

mochi_scheduler = Scheduler(owner=owner, pet=mochi)
luna_scheduler  = Scheduler(owner=owner, pet=luna)

# Helper
def print_conflicts(label: str, warnings: list[str]) -> None:
    print(f"\n{label}")
    if warnings:
        for w in warnings:
            print(w)
    else:
        print("  No conflicts detected.")

# ============================================================
# SCENARIO 1 — Same-pet conflict
# Mochi: "Morning walk" starts 08:00 (30 min) → ends 08:30
#         "Enrichment"   starts 08:15 (15 min) → ends 08:30
# Overlap: 08:15–08:30
# ============================================================
print("=" * 60)
print("SCENARIO 1: Same-pet conflict (Mochi)")
print("=" * 60)

mochi_scheduler.add_task(Task(
    name="Morning walk", duration=30, priority=1,
    start_time=time(8, 0),
))
mochi_scheduler.add_task(Task(
    name="Enrichment", duration=15, priority=2,
    start_time=time(8, 15),   # starts while Morning walk is still running
))
mochi_scheduler.add_task(Task(
    name="Feeding", duration=10, priority=1,
    start_time=time(9, 0),    # back-to-back, no overlap
))

for t in mochi_scheduler.tasks:
    print(f"  {t}")

print_conflicts("Conflict check:", mochi_scheduler.detect_conflicts())

# ============================================================
# SCENARIO 2 — Cross-pet conflict
# Mochi: "Feeding" at 09:00 (10 min) → ends 09:10
# Luna:  "Feeding" at 09:00 ( 5 min) → ends 09:05
# Jordan can't feed both pets at exactly the same time.
# ============================================================
print("\n" + "=" * 60)
print("SCENARIO 2: Cross-pet conflict (Mochi + Luna)")
print("=" * 60)

luna_scheduler.add_task(Task(
    name="Feeding", duration=5, priority=1,
    start_time=time(9, 0),    # same start as Mochi's Feeding
))
luna_scheduler.add_task(Task(
    name="Playtime", duration=20, priority=2,
    start_time=time(9, 30),   # no overlap with anything
))

print("Mochi tasks:")
for t in mochi_scheduler.tasks:
    print(f"  {t}")
print("Luna tasks:")
for t in luna_scheduler.tasks:
    print(f"  {t}")

print_conflicts(
    "Cross-pet conflict check:",
    mochi_scheduler.detect_conflicts(other=luna_scheduler),
)

# ============================================================
# SCENARIO 3 — Clean schedule (no conflicts)
# Tasks placed back-to-back with no overlaps.
# ============================================================
print("\n" + "=" * 60)
print("SCENARIO 3: Clean schedule (no conflicts expected)")
print("=" * 60)

clean_scheduler = Scheduler(owner=owner, pet=mochi)
clean_scheduler.add_task(Task(name="Feeding",      duration=10, priority=1, start_time=time(7, 0)))
clean_scheduler.add_task(Task(name="Morning walk", duration=30, priority=1, start_time=time(7, 10)))
clean_scheduler.add_task(Task(name="Enrichment",   duration=15, priority=2, start_time=time(7, 40)))

for t in clean_scheduler.tasks:
    print(f"  {t}")

print_conflicts("Conflict check:", clean_scheduler.detect_conflicts())
