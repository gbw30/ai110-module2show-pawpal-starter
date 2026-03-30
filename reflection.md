# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.

The three most important core actions are:

1. To Add/manage a task: tasks are the most important data since all other actions revolve around them (ex. scheduling)
2. Set owner + pet info: these are the constraints of the data for the schedule
3. Generate a daily schedule: this is the value of the app, it uses the data from #1 and constraints from #2 to create the schedule.

- What classes did you include, and what responsibilities did you assign to each?

The classes I included are Owner, Pet, Task, and Scheduler.
Owner has attributes name (str) and time_available (int) with a constructor __init__(name, time_available). No setter methods are needed since attributes are set at construction and can be reassigned directly.

Pet has attributes name (str) and species (str) with a constructor __init__(name, species). Same reasoning as Owner — no setter methods needed.

Task has attributes name (str), duration (int minutes) and priority (int x {x in between 1-3 where 1 is high and 3 is low}) with constructor __init__(name, duration, priority) and methods set_name, set_duration(minutes), set_priority(int), and __str__ for displaying the task in the Streamlit UI. Setters are kept here because tasks need to be editable after creation.

Scheduler has attributes owner (Owner), pet (Pet), tasks (list of Task) with methods add_task(Task), remove_task(Task), edit_task(Task, name, duration, priority), generate_plan() -> list of Task, and explain_plan() -> str.

The responsabilities are:
Owner: stores the human constraints
Pet: stores the pet's identity and constraints
Task: represents one unit of care work, so it knows what the care task is, its duration and importance. Manages its own data.
Scheduler: it is the brain. It maintaints the list of tasks, decides which tasks fit the owner's constraints, orders the tasks by priority, produces the final daily plan, and explain why it chose this plan for transparency.

**b. Design changes**

- Did your design change during implementation?
Yes. One attribute was added to the Scheduler class after a review identified a missing relationship in the skeleton.

- If yes, describe at least one change and why you made it.
planned_tasks function was added as an attribute on Scheduler because there was no place to store the generate_plan, which lead to explain_plan having nothing to reference.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
`generate_plan()` uses a greedy algorithm — it sorts tasks by priority and duration, then fills available time from the top down, accepting each task the moment it fits. This means it never backtracks. If a high-priority task is long and leaves a small gap, shorter lower-priority tasks that could fill that gap are simply excluded, even if a different ordering would fit more tasks in total.

- Why is that tradeoff reasonable for this scenario?
For a daily pet care app, priority correctness matters more than packing efficiency. An owner would rather guarantee that the most important tasks (feeding, medication) are always scheduled first and accept that a low-priority grooming task gets dropped, than have the scheduler rearrange priorities to squeeze in one extra task. The greedy approach also keeps the scheduling logic simple and predictable — the owner can understand why each task was or wasn't included.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
