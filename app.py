from datetime import date, timedelta
from datetime import time as dt_time

import streamlit as st

from pawpal_system import Owner, Pet, Scheduler, Task


PRIORITY_MAP = {"high": 1, "medium": 2, "low": 3}
PRIORITY_LABEL = {1: "High", 2: "Medium", 3: "Low"}


def build_scheduler(
    owner_name: str,
    pet_name: str,
    species: str,
    time_available: int,
    tasks: list[dict],
) -> Scheduler:
    """Create a Scheduler from the lightweight UI state."""
    scheduler = Scheduler(
        owner=Owner(name=owner_name, time_available=time_available),
        pet=Pet(name=pet_name, species=species),
    )
    for t in tasks:
        start = None
        if t.get("start_time"):
            h, m = map(int, t["start_time"].split(":"))
            start = dt_time(h, m)
        scheduler.add_task(
            Task(
                name=str(t["title"]),
                duration=int(t["duration_minutes"]),
                priority=PRIORITY_MAP[str(t["priority"])],
                completed=bool(t.get("completed", False)),
                recurrence=t.get("recurrence") or None,
                start_time=start,
            )
        )
    return scheduler


def find_task_idx(title: str, completed: bool) -> int | None:
    """Return the first session_state index matching title and completion status."""
    for i, t in enumerate(st.session_state.tasks):
        if t["title"] == title and t.get("completed", False) == completed:
            return i
    return None


# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")
st.caption("A daily care planner for busy pet owners.")

# ── Owner & Pet ───────────────────────────────────────────────────────────────

st.subheader("Owner & Pet")
col1, col2 = st.columns(2)
with col1:
    owner_name = st.text_input("Owner name", value="Jordan")
    time_available = st.number_input(
        "Daily time available (minutes)", min_value=1, max_value=1440, value=60
    )
with col2:
    pet_name = st.text_input("Pet name", value="Mochi")
    species = st.selectbox("Species", ["dog", "cat", "other"])

st.divider()

# ── Add a Task ────────────────────────────────────────────────────────────────

st.subheader("Add a Task")

if "tasks" not in st.session_state:
    st.session_state.tasks = []

c1, c2, c3 = st.columns(3)
with c1:
    task_title = st.text_input("Task title", value="Morning walk")
with c2:
    duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
with c3:
    priority = st.selectbox("Priority", ["high", "medium", "low"])

c4, c5 = st.columns(2)
with c4:
    recurrence = st.selectbox("Recurrence", ["none", "daily", "weekly"])
with c5:
    use_start_time = st.checkbox("Set a start time (conflict detection)")

start_time_str = None
if use_start_time:
    start_input = st.time_input("Start time", value=dt_time(8, 0))
    start_time_str = start_input.strftime("%H:%M")

if st.button("Add task", type="primary"):
    normalized = task_title.strip()
    if not normalized:
        st.warning("Task title cannot be empty.")
    else:
        duplicate = any(
            t["title"] == normalized and not t.get("completed", False)
            for t in st.session_state.tasks
        )
        if duplicate:
            st.warning(f'"{normalized}" already exists as an incomplete task.')
        else:
            st.session_state.tasks.append(
                {
                    "title": normalized,
                    "duration_minutes": int(duration),
                    "priority": priority,
                    "recurrence": recurrence if recurrence != "none" else None,
                    "completed": False,
                    "start_time": start_time_str,
                }
            )
            st.rerun()

st.divider()

# ── Task List ─────────────────────────────────────────────────────────────────

st.subheader("Task List")

if st.session_state.tasks:
    f_col, s_col = st.columns(2)
    with f_col:
        filter_status = st.selectbox(
            "Filter", ["All", "Incomplete", "Completed"], key="filter_status"
        )
    with s_col:
        sort_by = st.selectbox(
            "Sort by",
            ["Priority (default)", "Duration (shortest first)"],
            key="sort_by",
        )

    # Build the filtered + sorted view
    tasks_view = list(st.session_state.tasks)

    if filter_status == "Incomplete":
        tasks_view = [t for t in tasks_view if not t.get("completed", False)]
    elif filter_status == "Completed":
        tasks_view = [t for t in tasks_view if t.get("completed", False)]

    if sort_by == "Duration (shortest first)":
        tasks_view = sorted(tasks_view, key=lambda t: t["duration_minutes"])
    else:
        tasks_view = sorted(
            tasks_view,
            key=lambda t: (PRIORITY_MAP[t["priority"]], t["duration_minutes"]),
        )

    total = len(st.session_state.tasks)
    showing = len(tasks_view)
    done_count = sum(1 for t in st.session_state.tasks if t.get("completed", False))

    # Summary metrics row
    m1, m2, m3 = st.columns(3)
    m1.metric("Total tasks", total)
    m2.metric("Incomplete", total - done_count)
    m3.metric("Completed", done_count)

    st.caption(f"Showing {showing} of {total} task(s) — sorted by {sort_by.lower()}")

    if not tasks_view:
        st.info(f"No {filter_status.lower()} tasks to show.")
    else:
        # Overview table
        overview_tab, manage_tab = st.tabs(["Overview", "Manage Tasks"])

        with overview_tab:
            table_rows = [
                {
                    "Status": "Done" if t.get("completed") else "Pending",
                    "Task": t["title"],
                    "Duration (min)": t["duration_minutes"],
                    "Priority": t["priority"].capitalize(),
                    "Recurrence": t.get("recurrence") or "—",
                    "Start Time": t.get("start_time") or "—",
                }
                for t in tasks_view
            ]
            st.dataframe(table_rows, use_container_width=True, hide_index=True)

        with manage_tab:
            for task in tasks_view:
                completed = task.get("completed", False)
                priority_label = PRIORITY_LABEL[PRIORITY_MAP[task["priority"]]]
                recur_label = f" · {task['recurrence']}" if task.get("recurrence") else ""
                start_label = f" · starts {task['start_time']}" if task.get("start_time") else ""

                info_col, done_col, remove_col = st.columns([6, 1, 1])
                with info_col:
                    if completed:
                        st.markdown(
                            f"~~{task['title']}~~ — {task['duration_minutes']} min"
                            f" | {priority_label}{recur_label}{start_label}"
                        )
                    else:
                        st.markdown(
                            f"**{task['title']}** — {task['duration_minutes']} min"
                            f" | {priority_label}{recur_label}{start_label}"
                        )
                with done_col:
                    if not completed:
                        if st.button("Done", key=f"done_{task['title']}"):
                            idx = find_task_idx(task["title"], completed=False)
                            if idx is not None:
                                st.session_state.tasks[idx]["completed"] = True
                                rec = task.get("recurrence")
                                if rec == "daily":
                                    next_due = (date.today() + timedelta(days=1)).isoformat()
                                elif rec == "weekly":
                                    next_due = (date.today() + timedelta(weeks=1)).isoformat()
                                else:
                                    next_due = None
                                if next_due:
                                    st.session_state.tasks.append(
                                        {
                                            "title": task["title"],
                                            "duration_minutes": task["duration_minutes"],
                                            "priority": task["priority"],
                                            "recurrence": rec,
                                            "completed": False,
                                            "start_time": task.get("start_time"),
                                            "due_date": next_due,
                                        }
                                    )
                            st.rerun()
                with remove_col:
                    if st.button("Remove", key=f"remove_{task['title']}_{completed}"):
                        idx = find_task_idx(task["title"], completed=completed)
                        if idx is not None:
                            st.session_state.tasks.pop(idx)
                        st.rerun()

    st.markdown("")
    if st.button("Clear all tasks"):
        st.session_state.tasks = []
        st.rerun()

else:
    st.info("No tasks yet. Add one above.")

st.divider()

# ── Daily Schedule ────────────────────────────────────────────────────────────

st.subheader("Daily Schedule")
st.caption(
    "Builds a priority-first plan from incomplete tasks. "
    "High-priority tasks are always scheduled before lower-priority ones."
)

if st.button("Generate schedule", type="primary"):
    incomplete = [t for t in st.session_state.tasks if not t.get("completed", False)]
    if not incomplete:
        st.warning("No incomplete tasks to schedule. Add tasks or mark existing ones incomplete.")
    else:
        scheduler = build_scheduler(
            owner_name=owner_name,
            pet_name=pet_name,
            species=species,
            time_available=int(time_available),
            tasks=st.session_state.tasks,
        )

        # Conflict detection
        conflicts = scheduler.detect_conflicts()
        if conflicts:
            for w in conflicts:
                st.error(f"Conflict — {w.strip()}")
        else:
            st.success("No scheduling conflicts detected.")

        scheduler.generate_plan()

        if not scheduler.planned_tasks:
            st.warning("No tasks fit within the available time.")
        else:
            # Time budget metrics
            time_used = sum(t.duration for t in scheduler.planned_tasks)
            remaining = int(time_available) - time_used

            s1, s2, s3 = st.columns(3)
            s1.metric("Available", f"{int(time_available)} min")
            s2.metric("Scheduled", f"{time_used} min")
            s3.metric("Remaining", f"{remaining} min")

            # Scheduled tasks table
            st.markdown("**Scheduled tasks**")
            planned_rows = [
                {
                    "Task": t.name,
                    "Duration (min)": t.duration,
                    "Priority": PRIORITY_LABEL[t.priority],
                    "Recurrence": t.recurrence or "—",
                    "Start Time": t.start_time.strftime("%H:%M") if t.start_time else "—",
                }
                for t in scheduler.planned_tasks
            ]
            st.dataframe(planned_rows, use_container_width=True, hide_index=True)

            # Excluded tasks
            planned_names = {t.name for t in scheduler.planned_tasks}
            excluded = [
                t for t in scheduler.tasks
                if t.name not in planned_names and not t.completed
            ]
            if excluded:
                st.warning(
                    f"{len(excluded)} task(s) could not fit within the available time:"
                )
                excluded_rows = [
                    {
                        "Task": t.name,
                        "Duration (min)": t.duration,
                        "Priority": PRIORITY_LABEL[t.priority],
                    }
                    for t in excluded
                ]
                st.dataframe(excluded_rows, use_container_width=True, hide_index=True)
            else:
                st.success("All incomplete tasks fit within the available time.")
