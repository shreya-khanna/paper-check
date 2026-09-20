"""
Stage 5: Compute credibility score and category breakdown from verified audit answers.

Input:
    answers dict (from verify.py)

Output:
    dict containing:
        - "score": int between 0 and 100
        - "breakdown": summary statistics and per-question score mapping
"""

JUDGMENT_WEIGHTS = {
    "supported": 100.0,
    "insufficient": 50.0,
    "concern": 20.0,
    "inconsistency": 0.0,
}

def compute_score(answers: dict) -> dict:
    if not answers:
        return {
            "score": 0,
            "breakdown": {},
            "message": "No answers provided."
        }

    total_points = 0.0
    total_questions = 0

    breakdown = {}
    for qid, answer in answers.items():
        if not isinstance(answer, dict):
            continue

        judgment = str(answer.get("judgment", "insufficient")).lower()
        explanation = str(answer.get("explanation", "") or "")
        quote = str(answer.get("quote", "") or "")

        weight = JUDGMENT_WEIGHTS.get(judgment, 50.0)

        total_points += weight
        total_questions += 1

        breakdown[qid] = {
            "judgment": judgment,
            "weight": weight,
            "quote": quote,
            "explanation": explanation
        }

    final_score = round((total_points / total_questions) if total_questions else 0, 2)

    return {
        "score": int(final_score),
        "breakdown": breakdown
    }
