import streamlit as st

from pawpal_system import Owner, Pet, Scheduler, Task


PRIORITY_MAP = {"high": 1, "medium": 2, "low": 3}


def build_scheduler(
    owner_name: str,
    pet_name: str,
    species: str,
    time_available: int,
    tasks: list[dict[str, str | int]],
) -> Scheduler:
    """Create a Scheduler from the lightweight UI state."""
    scheduler = Scheduler(
        owner=Owner(name=owner_name, time_available=time_available),
        pet=Pet(name=pet_name, species=species),
    )
    for task_data in tasks:
        scheduler.add_task(
            Task(
                name=str(task_data["title"]),
                duration=int(task_data["duration_minutes"]),
                priority=PRIORITY_MAP[str(task_data["priority"])],
            )
        )
    return scheduler


st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ starter app.

This file stays intentionally thin. It gives you a working Streamlit app and a place to
demo your project, while the real scheduling behavior lives in your backend classes.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

Use this UI as the interactive layer on top of your scheduling system.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

st.subheader("Quick Demo Inputs")
owner_name = st.text_input("Owner name", value="Jordan")
pet_name = st.text_input("Pet name", value="Mochi")
species = st.selectbox("Species", ["dog", "cat", "other"])
time_available = st.number_input(
    "Daily time available (minutes)", min_value=1, max_value=1440, value=60
)

st.markdown("### Tasks")
st.caption("Add a few tasks. These are converted into Task objects when you build a schedule.")

if "tasks" not in st.session_state:
    st.session_state.tasks = []

col1, col2, col3 = st.columns(3)
with col1:
    task_title = st.text_input("Task title", value="Morning walk")
with col2:
    duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
with col3:
    priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)

add_col, clear_col = st.columns([1, 1])
with add_col:
    if st.button("Add task"):
        normalized_title = task_title.strip()
        if not normalized_title:
            st.warning("Task title cannot be empty.")
        else:
            st.session_state.tasks.append(
                {
                    "title": normalized_title,
                    "duration_minutes": int(duration),
                    "priority": priority,
                }
            )
            st.rerun()
with clear_col:
    if st.button("Clear tasks"):
        st.session_state.tasks = []
        st.rerun()

if st.session_state.tasks:
    st.write("Current tasks:")
    st.table(st.session_state.tasks)
else:
    st.info("No tasks yet. Add one above.")

st.divider()

st.subheader("Build Schedule")
st.caption("This button calls your scheduling logic and displays the resulting plan.")

if st.button("Generate schedule"):
    if not st.session_state.tasks:
        st.warning("Add at least one task before generating a schedule.")
    else:
        scheduler = build_scheduler(
            owner_name=owner_name,
            pet_name=pet_name,
            species=species,
            time_available=int(time_available),
            tasks=st.session_state.tasks,
        )
        scheduler.generate_plan()
        st.success("Schedule generated.")
        st.text(scheduler.explain_plan())
