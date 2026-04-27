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

I used AI for brainstorming, debugging, and refactoring code. I generated the initial code with claude and I assigned it multiple constraints to ensure alignment with system design. I ran QA tests on the local instance to ensure project functions as required, then using AI to debug errors found through QA. I used Windsurf explain to have a deeper, more thorough understanding of the AI generated code to find faults for refactoring. I also used AI for design brainstorming by creating a feedback loop with it and updating the design as needed (for example, from MVP to full project architecture).

- What kinds of prompts or questions were most helpful?

Reiterate as many times as necessary and run e2e tests after every change. Ensure new features align with project design. Document changes. etc.

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.

The AI wanted to implement unnecessary setter functions for Owner and Pet when not necessary.

- How did you evaluate or verify what the AI suggested?

I reprompted the AI questioning the previous results so that it could rereason them, therefore realizing it is unnecessary. 

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?

I tested task addition, time-limit handling in generate_plan, priority ordering, shortest-duration tie breaking, exact-fit scheduling, skipping completed tasks, recurring task regeneration (daily and weekly), duplicate prevention, conflict detection, and filtering by pet name.

- Why were these tests important?

These tests mattered because they cover the main promises of the system. The scheduler must respect available time, choose the most important tasks first, avoid adding duplicate incomplete tasks, and correctly handle recurring tasks after completion. I also tested conflicts because a schedule is not useful if two tasks overlap in time without warning.

**b. Confidence**

- How confident are you that your scheduler works correctly?

I am reasonably confident that the scheduler works correctly for the main use cases. The core scheduling rules were tested directly with pytest, and I also ran manual QA on the Streamlit app to make sure the UI triggered the expected behavior. I would give it 5 stars (as seen in the README.md)

- What edge cases would you test next if you had more time?

If I had more time, I would test larger task lists, tasks with the same priority and same duration, empty schedules, very small and very large time limits, and more complex overlap cases across multiple pets. I would also test cases where the greedy algorithm leaves unused time even though a different combination of tasks could fit more total work.

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

The final product worked properly. It was satisfying to see it complete.

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

I would improve the UI, it is too basic and barebones. Maybe add user login. Google calendar integratinon would be nice too.

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?

Ai is a really good tool for developing systems, but they have to be kept in check as they tend to produce unnecessary complexity.

---

## 6. AI Extension: Reflection and Ethics

**What are the limitations or biases in the AI system?**

The AI Assistant is intentionally local-first, which makes it reliable and free-tier friendly, but the regex parser can miss unusual phrasing. The local pet-care knowledge base is also limited to the curated entries in `pet_knowledge.py`, so it may not cover every species, breed, age, or medical situation. If Gemini is used as a fallback classifier, it can still misclassify ambiguous requests, which is why the app validates every structured action before changing task state.

**Could the AI be misused, and how would you prevent that?**

The biggest misuse risk is treating PawPal+ like veterinary or emergency medical advice. The system should be used for organizing care routines, not diagnosing illness or deciding treatment. I reduced this risk by keeping AI actions structured, validating every task update, using curated local guidance for common questions, and making the human owner responsible for reviewing outputs before acting on them.

**What surprised you while testing reliability?**

The biggest surprise was that Gemini free-tier `429 RESOURCE_EXHAUSTED` errors could happen even with a fresh API key and a fresh Google AI Studio project. That changed the design: instead of calling Gemini for every assistant request, I moved common task commands and common pet-care Q&A into local code and added an in-app reliability check that can run without any Gemini quota.

**How did you collaborate with AI during this project?**

A helpful AI suggestion was to add a reliability evaluation system that measures the assistant's structured actions and exposes the results in the Streamlit app. A flawed AI suggestion was to rely too heavily on Gemini for every interaction, which made the project more fragile because of quota limits. I improved that by changing Gemini into an optional classifier and keeping the Scheduler and local validation as the source of truth.
