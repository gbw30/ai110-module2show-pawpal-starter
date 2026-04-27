# PawPal+ Model Card

## Project Overview

PawPal+ is a Streamlit pet-care planning app. The base project was a deterministic scheduler for adding pet-care tasks, detecting conflicts, handling recurring work, and generating a daily plan from the owner's available time.

The AI extension adds a local-first assistant, a local pet-care knowledge base, optional Gemini classifier fallback, and an in-app reliability evaluator.

## AI Capabilities

- **Local task assistant:** Parses common requests such as adding, removing, completing, listing, and scheduling tasks without an API call.
- **Local RAG Q&A:** Retrieves curated pet-care guidance from `pet_knowledge.py` for common dog, cat, and general pet-care questions.
- **Optional Gemini classifier:** Uses Gemini only when local parsing or local RAG cannot handle the request. Gemini returns structured action fields instead of directly changing app state.
- **Reliability evaluator:** Runs deterministic checks in the Streamlit app and reports pass/fail results, source, capability category, and errors.

## System Role And Data Flow

1. The user enters a request in the Streamlit UI.
2. `ai_assistant.py` tries local parsing first.
3. Pet-care questions use `pet_knowledge.py` for keyword-based retrieval.
4. Ambiguous requests may use Gemini as a fallback classifier.
5. `app.py` validates the returned structured action.
6. `pawpal_system.py` remains the source of truth for scheduling, recurrence, and conflict detection.
7. The user reviews the visible task list, schedule output, or reliability results.

## Intended Use

PawPal+ is intended to help pet owners organize routine care tasks and understand common care guidance. It is useful for planning feeding, walking, grooming, enrichment, and other daily care responsibilities.

The app is not intended to diagnose illness, replace a veterinarian, or provide emergency medical advice.

## Limitations And Biases

- The local parser uses regex rules, so unusual phrasing can be missed.
- The local knowledge base is curated and small; it does not cover every animal, breed, age, medical condition, or regional care issue.
- Gemini can still misclassify ambiguous requests when fallback is used.
- Knowledge entries are general-purpose and may not apply to every individual pet.

## Guardrails

- Local-first design avoids unnecessary Gemini calls and reduces quota failures.
- Gemini never directly mutates app state.
- `app.py` validates task names, durations, priorities, recurrence values, and task existence before applying AI-suggested changes.
- 429 quota errors are caught and shown safely with retry timing.
- The AI Reliability Check runs without Gemini by default.

## Reliability And Testing Results

The project currently has `39 passed` automated tests.

Test coverage includes:

- Scheduler behavior: task addition, recurrence, filtering, conflict detection, and priority-first planning.
- AI assistant behavior: context building, local parsing, local RAG, rate limiting, 429 handling, and invalid-response handling.
- Knowledge base behavior: retrieval relevance, species filtering, unknown-question handling, and Gemini context formatting.
- Reliability evaluator behavior: no-API default checks, expected structured actions, pass-rate reporting, and live Gemini failure isolation.

The in-app AI Reliability Check evaluates:

- local task creation
- natural-language add phrasing
- task completion
- task removal
- task listing
- schedule guidance
- local RAG Q&A
- missing API key guardrail
- optional live Gemini smoke test

## AI Collaboration Reflection

A helpful AI suggestion was adding an integrated reliability evaluation system so the project could prove the assistant works. A flawed AI suggestion was relying too heavily on Gemini for every interaction, which caused quota problems and made the app less dependable. The final design keeps AI useful but constrained: local code handles common cases, Gemini is optional, and deterministic validation remains in control.

## Misuse And Ethics

The main misuse risk is treating PawPal+ like veterinary advice. To reduce this risk, the app frames AI output as routine care guidance and scheduling support. Users should contact a veterinarian for health concerns, medication questions, emergencies, or symptoms.

## Submission Notes

- GitHub repository: https://github.com/gbw30/ai110-module2show-pawpal-starter
- Loom walkthrough: replace `YOUR_LOOM_LINK_HERE` in `README.md` after recording the final demo.
