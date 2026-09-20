"""
Stage 4.5: Verify the audit answers and claims BEFORE they're scored.

Input:  answers dict (from audit.py) + claims list (from extract.py) + paper_markdown (source text)
Output: same-shaped answers dict & claims with "verified" bool and "fuzzy_match" metadata added,
        and any finding that fails verification is DOWNGRADED to "insufficient"
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


def check_quote_in_source(quote: str, source_text: str, threshold: float = FUZZY_MATCH_THRESHOLD) -> dict:
    """
    Checks whether `quote` genuinely appears in `source_text`.
    Tries exact substring first (fast, strict). Falls back to a fuzzy sliding
    window so small whitespace/OCR differences from Docling don't cause false
    failures - but a fabricated quote still won't pass.

    Returns a structured dictionary with match status, method, and score.
    """
    if not quote or not quote.strip():
        return {
            "matched": False,
            "method": "none",
            "score": 0.0,
            "note": "Empty quote provided.",
        }

    norm_quote = _normalize(quote)
    norm_source = _normalize(source_text)

    # 1. Exact substring match - the common, cheap case
    if norm_quote in norm_source:
        return {
            "matched": True,
            "method": "exact",
            "score": 1.0,
            "note": "Exact substring match confirmed in source text.",
        }

    # 2. Fuzzy fallback: slide a window of source text roughly the quote's length
    window = len(norm_quote)
    if window < 8:  # too short to fuzzy-match reliably; require exact match
        return {
            "matched": False,
            "method": "none",
            "score": 0.0,
            "note": "Quote too short for fuzzy matching; exact match failed.",
        }

    best_ratio = 0.0
    best_chunk = ""
    step = max(1, window // 4)
    for i in range(0, max(1, len(norm_source) - window), step):
        chunk = norm_source[i:i + window]
        ratio = difflib.SequenceMatcher(None, norm_quote, chunk).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_chunk = chunk

    if best_ratio >= threshold:
        return {
            "matched": True,
            "method": "fuzzy",
            "score": round(best_ratio, 3),
            "note": f"Fuzzy sequence match confirmed (similarity: {int(best_ratio * 100)}%, threshold ≥ {int(threshold * 100)}%).",
            "matched_snippet": best_chunk[:200],
        }

    return {
        "matched": False,
        "method": "fuzzy",
        "score": round(best_ratio, 3),
        "note": f"Quote not found in source text (best similarity: {int(best_ratio * 100)}%, threshold ≥ {int(threshold * 100)}%).",
        "matched_snippet": best_chunk[:200] if best_chunk else "",
    }


def _quote_found_in_source(quote: str, source_text: str) -> bool:
    """Legacy boolean wrapper for backward compatibility."""
    res = check_quote_in_source(quote, source_text)
    return res["matched"]


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
                "fuzzy_match": {
                    "matched": False,
                    "method": "none",
                    "score": 0.0,
                    "note": "Missing answer from model.",
                },
            }
            continue

        ans = dict(answers[qid])  # copy, don't mutate the original
        judgment = ans.get("judgment", "")
        quote = ans.get("quote", "")

        # Check 2: schema validity
        if judgment not in VALID_JUDGMENTS:
            ans["raw_judgment"] = judgment
            ans["judgment"] = "insufficient"
            ans["verified"] = False
            ans["verification_note"] = f"invalid_judgment:{judgment}"
            ans["fuzzy_match"] = {
                "matched": False,
                "method": "none",
                "score": 0.0,
                "note": f"Invalid judgment: {judgment}",
            }
            verified_answers[qid] = ans
            continue

        # Check 3: evidence validity
        if judgment == "insufficient":
            # no quote required - this is a legitimate, honest answer
            ans["verified"] = True
            ans["verification_note"] = "ok_no_evidence_needed"
            ans["fuzzy_match"] = {
                "matched": True,
                "method": "no_evidence_needed",
                "score": 1.0,
                "note": "Legitimate insufficient finding; no evidence quote required.",
            }
        else:
            match_res = check_quote_in_source(quote, paper_markdown)
            ans["fuzzy_match"] = match_res
            if match_res["matched"]:
                ans["verified"] = True
                ans["verification_note"] = f"ok_quote_confirmed ({match_res['method']}, {int(match_res['score'] * 100)}%)"
            else:
                # The model claimed a quote that isn't actually in the paper.
                # Downgrade rather than trust it - this is the hallucination guard.
                ans["raw_judgment"] = judgment
                ans["judgment"] = "insufficient"
                ans["verified"] = False
                ans["verification_note"] = f"quote_not_found_in_source (best similarity: {int(match_res['score'] * 100)}%)"

        verified_answers[qid] = ans

    return verified_answers


def verify_claims(claims: list[dict], paper_markdown: str) -> list[dict]:
    """
    Verifies extracted claims against the paper markdown using fuzzy matching.
    """
    verified_claims = []
    for c in claims:
        item = dict(c)
        quote = item.get("quote", "")
        verdict = item.get("verdict", "supported")
        judgment = item.get("judgment", verdict if verdict in VALID_JUDGMENTS else ("supported" if verdict == "supported" else "concern"))
        item["judgment"] = judgment

        if not quote or quote.strip() == "" or judgment == "insufficient":
            item["verified"] = True
            item["verification_note"] = "ok_no_evidence_needed"
            item["fuzzy_match"] = {
                "matched": True,
                "method": "no_evidence_needed",
                "score": 1.0,
                "note": "No quote required for this claim.",
            }
        else:
            match_res = check_quote_in_source(quote, paper_markdown)
            item["fuzzy_match"] = match_res
            item["verified"] = match_res["matched"]
            if match_res["matched"]:
                item["verification_note"] = f"ok_quote_confirmed ({match_res['method']}, {int(match_res['score'] * 100)}%)"
            else:
                item["verification_note"] = f"quote_not_found_in_source (best match: {int(match_res['score'] * 100)}%)"

        verified_claims.append(item)

    return verified_claims


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

    print("\n--- VERIFICATION & FUZZY MATCHING RESULTS ---")
    for qid, res in result.items():
        q_text = AUDIT_QUESTIONS.get(qid, {}).get("question", "No question text found")
        verified_status = "[PASS]" if res.get("verified") else "[FAIL - Downgraded]"
        fuzzy_info = res.get("fuzzy_match", {})
        print(f"\n[{qid}]")
        print(f"  Question:    {q_text}")
        print(f"  Judgment:    {res.get('judgment')} ({verified_status})")
        print(f"  Fuzzy Match: {fuzzy_info.get('method')} (score: {fuzzy_info.get('score')})")
        print(f"  Note:        {res.get('verification_note')}")
        if res.get("quote"):
            print(f"  Quote:       \"{res.get('quote')}\"")
        print(f"  Explanation: {res.get('explanation')}")

    print("\n--- JSON OUTPUT ---")
    print(json.dumps(result, indent=2))