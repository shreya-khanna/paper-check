"""
Stage 4.5: Verify the audit answers BEFORE they're scored.

Input:  answers dict (from audit.py) + paper_markdown (the source text)
Output: same-shaped answers dict, but with a "verified" bool added to each,
        and any answer that fails verification is DOWNGRADED to "insufficient"
        so a hallucinated quote can never inflate the score.

No LLM call here - this is deterministic checking, same philosophy as score.py.
"""

import difflib
import re
import os
import sys
import json

from questions import AUDIT_QUESTIONS

VALID_JUDGMENTS = {"supported", "concern", "insufficient", "inconsistency"}

# how loosely a quote is allowed to match the source text (0-1, higher = stricter)
FUZZY_MATCH_THRESHOLD = 0.85


def _normalize(text: str) -> str:
    """Collapse whitespace/case so minor formatting differences don't fail a match."""
    return re.sub(r"\s+", " ", text.strip().lower())


def _quote_found_in_source(quote: str, source_text: str) -> bool:
    """
    Checks whether `quote` genuinely appears in `source_text`.
    Tries exact substring first (fast, strict). Falls back to a fuzzy sliding
    window so small whitespace/OCR differences from Docling don't cause false
    failures - but a fabricated quote still won't pass.
    """
    if not quote or not quote.strip():
        return False

    norm_quote = _normalize(quote)
    norm_source = _normalize(source_text)

    # 1. Exact substring match - the common, cheap case
    if norm_quote in norm_source:
        return True

    # 2. Fuzzy fallback: slide a window of source text roughly the quote's
    #    length and check similarity. Catches near-verbatim quotes without
    #    letting a fully invented sentence through.
    window = len(norm_quote)
    if window < 8:  # too short to fuzzy-match reliably; require exact match
        return False

    step = max(1, window // 4)
    for i in range(0, max(1, len(norm_source) - window), step):
        chunk = norm_source[i:i + window]
        ratio = difflib.SequenceMatcher(None, norm_quote, chunk).ratio()
        if ratio >= FUZZY_MATCH_THRESHOLD:
            return True

    return False


def _normalize_answer_object(qid: str, answer: dict) -> dict:
    if answer is None:
        answer = {}

    normalized = {
        "question_id": qid,
        "judgment": str(answer.get("judgment", "insufficient")).lower(),
        "quote": str(answer.get("quote", "") or ""),
        "explanation": str(answer.get("explanation", "") or "No explanation provided."),
        "verified": False,
        "verification_note": "normalized_missing_fields",
    }

    return normalized


def verify_answers(answers: dict, paper_markdown: str) -> dict:
    """
    Runs three checks on the audit output, in order:

      1. Completeness  - every question in AUDIT_QUESTIONS was actually answered
      2. Schema         - judgment is one of the 4 allowed values
      3. Evidence        - the quote genuinely exists in the source paper,
                            OR judgment is legitimately "insufficient" (no quote required)

    Any failure downgrades that answer to judgment="insufficient" and tags it
    verified=False with a reason - it can never silently inflate the score.
    """
    verified_answers = {}

    for qid in AUDIT_QUESTIONS:
        if qid not in answers:
            # Model skipped a question entirely - do not let it disappear silently
            verified_answers[qid] = {
                "question_id": qid,
                "judgment": "insufficient",
                "quote": "",
                "explanation": "Model did not answer this question.",
                "verified": False,
                "verification_note": "missing_answer",
            }
            continue

        ans = _normalize_answer_object(qid, answers[qid])
        judgment = ans.get("judgment", "insufficient")
        quote = ans.get("quote", "")

        if judgment not in VALID_JUDGMENTS:
            ans["judgment"] = "insufficient"
            ans["verified"] = False
            ans["verification_note"] = f"invalid_judgment:{judgment}"
            verified_answers[qid] = ans
            continue

        if judgment == "insufficient":
            # no quote required - this is a legitimate, honest answer
            ans["verified"] = True
            ans["verification_note"] = "ok_no_evidence_needed"
        else:
            if _quote_found_in_source(quote, paper_markdown):
                ans["verified"] = True
                ans["verification_note"] = "ok_quote_confirmed"
            else:
                # The model claimed a quote that isn't actually in the paper.
                # Downgrade rather than trust it - this is the hallucination guard.
                ans["judgment"] = "insufficient"
                ans["verified"] = False
                ans["verification_note"] = "quote_not_found_in_source"

        verified_answers[qid] = ans

    return verified_answers


if __name__ == "__main__":
    import glob

    answers = None
    source_text = None

    if len(sys.argv) >= 3:
        answers_file = sys.argv[1]
        markdown_file = sys.argv[2]

        if os.path.exists(answers_file) and os.path.exists(markdown_file):
            with open(answers_file, "r", encoding="utf-8") as af:
                answers = json.load(af)
            with open(markdown_file, "r", encoding="utf-8") as mf:
                source_text = mf.read()
            print(f"Verifying answers from '{answers_file}' against '{markdown_file}'...\n")

    if answers is None or source_text is None:
        print("Running verification test using AUDIT_QUESTIONS checklist...\n")
        available_mds = glob.glob("outputs/*.md") + glob.glob("backend/outputs/*.md")
        if available_mds:
            latest_md = max(available_mds, key=os.path.getmtime)
            with open(latest_md, "r", encoding="utf-8") as f:
                source_text = f.read()
            fake_quote_sample = "Improving road safety is critical for the sustainable development of cities."
        else:
            source_text = "Improving road safety is critical for the sustainable development of cities."
            fake_quote_sample = source_text

        fake_answers = {
            "data_preprocessing": {
                "question_id": "data_preprocessing",
                "judgment": "supported",
                "quote": fake_quote_sample,
                "explanation": "Authors describe data collection procedures and preprocessing.",
            },
            "leakage": {
                "question_id": "leakage",
                "judgment": "concern",
                "quote": "This sentence was hallucinated and never written in the paper.",
                "explanation": "Potential risk of overlap.",
            },
            "evaluation": {
                "question_id": "evaluation",
                "judgment": "insufficient",
                "quote": "",
                "explanation": "No evaluation details were reported in the text.",
            },
        }
        answers = fake_answers

    result = verify_answers(answers, source_text)

    print("\n--- VERIFICATION RESULTS ---")
    for qid, res in result.items():
        q_text = AUDIT_QUESTIONS.get(qid, {}).get("question", "No question text found")
        verified_status = "[PASS]" if res.get("verified") else "[FAIL - Downgraded]"
        print(f"\n[{qid}]")
        print(f"  Question:    {q_text}")
        print(f"  Judgment:    {res.get('judgment')} ({verified_status})")
        print(f"  Note:        {res.get('verification_note')}")
        if res.get("quote"):
            print(f"  Quote:       \"{res.get('quote')}\"")
        print(f"  Explanation: {res.get('explanation')}")

    print("\n--- JSON OUTPUT ---")
    print(json.dumps(result, indent=2))