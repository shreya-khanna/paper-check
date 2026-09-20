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
            "breakdown": {
                "supported": 0,
                "insufficient": 0,
                "concern": 0,
                "inconsistency": 0,
                "total_questions": 0,
            }
        }

    total_points = 0.0
    counts = {
        "supported": 0,
        "insufficient": 0,
        "concern": 0,
        "inconsistency": 0,
    }
    details = {}

    for qid, ans in answers.items():
        judgment = ans.get("judgment", "insufficient")
        is_verified = ans.get("verified", True)

        # Fallback to insufficient if not verified or invalid judgment
        if not is_verified or judgment not in JUDGMENT_WEIGHTS:
            effective_judgment = "insufficient"
        else:
            effective_judgment = judgment

        pts = JUDGMENT_WEIGHTS[effective_judgment]
        total_points += pts
        counts[effective_judgment] = counts.get(effective_judgment, 0) + 1
        details[qid] = {
            "judgment": effective_judgment,
            "raw_judgment": judgment,
            "points": pts,
            "verified": is_verified,
        }

    num_questions = len(answers)
    final_score = int(round(total_points / num_questions)) if num_questions > 0 else 0

    return {
        "score": max(0, min(100, final_score)),
        "breakdown": {
            **counts,
            "total_questions": num_questions,
            "details": details,
        }
    }
