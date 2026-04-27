"""PawPal+ pet-care knowledge base with keyword-based retrieval.

Provides species-specific care guidance that can answer common questions
locally (zero API calls) or augment a Gemini prompt with curated context.
"""

from __future__ import annotations

import re

# ── Knowledge base ───────────────────────────────────────────────────────────
# Each entry has: category, species (list), keywords (for matching),
# and content (the answer text).

KNOWLEDGE_BASE: list[dict] = [
    # ── Dog: Exercise ──
    {
        "category": "exercise",
        "species": ["dog"],
        "keywords": ["walk", "exercise", "run", "play", "active", "energy", "outdoor"],
        "content": (
            "Most adult dogs need 30-60 minutes of exercise per day, split into "
            "two or more sessions. High-energy breeds (huskies, border collies, "
            "retrievers) may need 1-2 hours. Puppies need shorter, more frequent "
            "play sessions (5 minutes per month of age, twice daily). Senior dogs "
            "benefit from gentle 15-20 minute walks."
        ),
    },
    # ── Dog: Feeding ──
    {
        "category": "feeding",
        "species": ["dog"],
        "keywords": ["feed", "food", "eat", "meal", "diet", "hungry", "nutrition", "treat"],
        "content": (
            "Adult dogs typically eat twice a day (morning and evening). Puppies "
            "under 6 months should eat 3 times a day, then transition to twice "
            "daily. Portion size depends on weight, breed, and activity level — "
            "check the food packaging or ask your vet. Fresh water should always "
            "be available. Avoid chocolate, grapes, onions, and xylitol."
        ),
    },
    # ── Dog: Grooming ──
    {
        "category": "grooming",
        "species": ["dog"],
        "keywords": ["groom", "brush", "bath", "nail", "fur", "coat", "shed", "clean", "wash"],
        "content": (
            "Brushing frequency depends on coat type: short coats need weekly "
            "brushing, long or double coats need brushing every 1-2 days. Baths "
            "are typically needed every 4-8 weeks unless the dog gets dirty. Nails "
            "should be trimmed every 2-4 weeks. Check and clean ears weekly, "
            "especially for floppy-eared breeds."
        ),
    },
    # ── Dog: Health ──
    {
        "category": "health",
        "species": ["dog"],
        "keywords": ["vet", "health", "sick", "vaccine", "medication", "checkup", "flea", "tick", "worm"],
        "content": (
            "Annual vet checkups are recommended for adult dogs, twice yearly for "
            "seniors (7+ years). Core vaccines include rabies, distemper, and "
            "parvovirus. Flea/tick and heartworm prevention should be given "
            "year-round in most climates. Watch for changes in appetite, energy, "
            "or behavior as early signs of illness."
        ),
    },
    # ── Dog: Training ──
    {
        "category": "training",
        "species": ["dog"],
        "keywords": ["train", "obedience", "command", "behavior", "trick", "sit", "stay", "recall"],
        "content": (
            "Short, positive training sessions (5-15 minutes) are most effective. "
            "Use treats and praise as rewards. Consistency across all family "
            "members is important. Start with basic commands: sit, stay, come, "
            "and leash walking. Puppies can begin socialization and basic training "
            "as early as 8 weeks."
        ),
    },
    # ── Cat: Exercise ──
    {
        "category": "exercise",
        "species": ["cat"],
        "keywords": ["play", "exercise", "active", "energy", "toy", "laser", "enrichment"],
        "content": (
            "Indoor cats need 15-30 minutes of interactive play daily, split into "
            "short sessions. Use wand toys, laser pointers (always end with a "
            "physical toy to catch), or puzzle feeders. Provide vertical space "
            "(cat trees, shelves) for climbing. Window perches offer mental "
            "stimulation."
        ),
    },
    # ── Cat: Feeding ──
    {
        "category": "feeding",
        "species": ["cat"],
        "keywords": ["feed", "food", "eat", "meal", "diet", "hungry", "nutrition", "treat"],
        "content": (
            "Adult cats typically eat 2-3 small meals per day. Kittens under 6 "
            "months should eat 3-4 times daily. Cats are obligate carnivores and "
            "need high-protein, meat-based diets. Fresh water should always be "
            "available — some cats prefer running water (fountains). Avoid milk, "
            "onions, garlic, and raw fish."
        ),
    },
    # ── Cat: Grooming ──
    {
        "category": "grooming",
        "species": ["cat"],
        "keywords": ["groom", "brush", "bath", "nail", "fur", "coat", "shed", "clean"],
        "content": (
            "Short-haired cats need brushing once a week; long-haired cats need "
            "daily brushing to prevent mats. Most cats rarely need baths. Nails "
            "should be trimmed every 2-3 weeks. Clean the litter box daily and "
            "replace litter fully every 1-2 weeks."
        ),
    },
    # ── Cat: Health ──
    {
        "category": "health",
        "species": ["cat"],
        "keywords": ["vet", "health", "sick", "vaccine", "medication", "checkup", "flea", "worm"],
        "content": (
            "Annual vet checkups are recommended; twice yearly for senior cats "
            "(10+ years). Core vaccines include rabies, feline distemper (FVRCP), "
            "and feline leukemia for outdoor cats. Indoor cats still need flea "
            "prevention. Watch for changes in litter box habits, appetite, or "
            "hiding behavior as early illness signs."
        ),
    },
    # ── General: Scheduling ──
    {
        "category": "scheduling",
        "species": ["dog", "cat", "other"],
        "keywords": ["schedule", "routine", "plan", "time", "daily", "when", "how often", "frequency"],
        "content": (
            "Pets thrive on consistent daily routines. Try to feed, walk, and "
            "play at the same times each day. Morning and evening are natural "
            "anchor points. Space tasks apart to avoid rushing — a calm routine "
            "is better than a packed one. Use PawPal's scheduler to prioritize "
            "high-priority tasks (feeding, medication) and fit in optional ones "
            "(grooming, enrichment) when time allows."
        ),
    },
    # ── General: New pet ──
    {
        "category": "getting_started",
        "species": ["dog", "cat", "other"],
        "keywords": ["new", "first", "adopt", "puppy", "kitten", "beginner", "start", "prepare"],
        "content": (
            "New pets need a safe, quiet space to adjust. Stock up on food, "
            "bowls, bedding, and species-appropriate toys before arrival. Schedule "
            "a vet visit within the first week. Introduce house rules early and "
            "be consistent. Expect an adjustment period of 2-4 weeks — patience "
            "and routine are key."
        ),
    },
]


# ── Retrieval ────────────────────────────────────────────────────────────────

def retrieve(question: str, species: str, top_k: int = 3) -> list[dict]:
    """Return the top_k most relevant knowledge entries for a question + species.

    Scoring: each keyword match in the question adds 1 point.  Species match
    adds 2 points.  Results are sorted by score descending.  Only entries with
    score > 0 are returned.
    """
    lowered = question.lower()
    species_lower = species.lower()
    scored: list[tuple[int, dict]] = []

    for entry in KNOWLEDGE_BASE:
        score = 0
        # Species relevance
        if species_lower in entry["species"] or "other" in entry["species"]:
            score += 2

        # Keyword matches
        for kw in entry["keywords"]:
            if kw in lowered:
                score += 1

        # Category match (if user mentions category directly)
        if entry["category"] in lowered:
            score += 1

        if score > 0:
            scored.append((score, entry))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [entry for _, entry in scored[:top_k]]


def answer_from_knowledge(question: str, species: str) -> str | None:
    """Try to answer a pet-care question from the knowledge base.

    Returns a formatted answer string if relevant entries are found,
    or None if the knowledge base can't help.
    """
    entries = retrieve(question, species, top_k=2)
    if not entries:
        return None

    # Require at least one keyword match beyond just species
    best_score = 0
    lowered = question.lower()
    for entry in entries:
        kw_hits = sum(1 for kw in entry["keywords"] if kw in lowered)
        best_score = max(best_score, kw_hits)

    if best_score == 0:
        return None

    parts = []
    for entry in entries:
        parts.append(entry["content"])

    return " ".join(parts)


def format_context_for_gemini(entries: list[dict]) -> str:
    """Format retrieved entries as compact context for a Gemini prompt."""
    if not entries:
        return ""
    lines = ["PET CARE REFERENCE:"]
    for entry in entries:
        lines.append(f"[{entry['category']}] {entry['content']}")
    return "\n".join(lines)
