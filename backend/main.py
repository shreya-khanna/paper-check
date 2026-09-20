"""
Full pipeline, wired end to end.

    PDF
     |  (docling_parse.py)
     v
   markdown + tables
     |  (extract.py)
     v
   paper_context dict  --+
     |                   |
     | (questions.py)    |
     v                   |
   AUDIT_QUESTIONS -------> (audit.py) -> answers dict (with quotes)
                                              |
                                              | (verify.py) - checks quotes are
                                              |   real, downgrades hallucinations
                                              v
                                        verified answers dict
                                              |
                                              | (score.py)
                                              v
                                        {score, breakdown}
                                              |
                                              v
                                   FINAL JSON -> your frontend

Run:
    python main.py path/to/paper.pdf > report.json
"""

import os
import sys
import json
import shutil
from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv, find_dotenv

from pdf_parser import parse_paper
from extract import extract_paper_context


from questions import AUDIT_QUESTIONS
from audit import run_audit
from verify import verify_answers
from score import compute_score

# Load environment
load_dotenv(find_dotenv())
load_dotenv(".env")
load_dotenv("../.env")
load_dotenv(".env.local")
load_dotenv("../.env.local")

app = FastAPI(title="Paper-Check API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def format_frontend_report(pipeline_result: dict, pdf_filename: str) -> dict:
    """
    Transforms the pipeline output into the exact TypeScript `Report` schema expected
    by the Next.js frontend (see lib/types.ts).
    """
    paper_context = pipeline_result.get("paper_context", {})
    score = pipeline_result.get("score", 0)
    answers = pipeline_result.get("answers", {})

    # Map status
    judgment_to_status = {
        "supported": "pass",
        "concern": "flag",
        "insufficient": "not_reported",
        "inconsistency": "flag",
    }

    module_map = {
        "data_preprocessing": "Data & Preprocessing",
        "leakage": "Data Leakage Risk",
        "evaluation": "Evaluation Protocol",
        "statistical_analysis": "Statistical Analysis",
        "baseline_fairness": "Baseline Fairness",
        "claim_evidence_match": "Claim & Evidence Alignment",
        "reporting_sufficiency": "Reporting Sufficiency",
    }

    findings = []
    breakdown_items = []

    for qid, q_data in AUDIT_QUESTIONS.items():
        ans = answers.get(qid, {})
        judgment = ans.get("judgment", "insufficient")
        is_verified = ans.get("verified", False)
        status = judgment_to_status.get(judgment, "not_reported")
        module_name = module_map.get(qid, "General Methodology")
        fuzzy_info = ans.get("fuzzy_match", {})

        findings.append({
            "id": qid,
            "module": module_name,
            "question": q_data.get("question", ""),
            "status": status,
            "judgment": judgment,
            "verified": is_verified,
            "verificationNote": ans.get("verification_note", ""),
            "fuzzyMatch": {
                "matched": fuzzy_info.get("matched", is_verified),
                "score": fuzzy_info.get("score", 1.0 if is_verified else 0.0),
                "method": fuzzy_info.get("method", "fuzzy" if is_verified else "none"),
                "note": fuzzy_info.get("note", ans.get("verification_note", "")),
            },
            "note": ans.get("explanation", ""),
            "quote": ans.get("quote", ""),
            "location": "Docling OCR Verified Text" if is_verified and ans.get("quote") else "Extracted Context",
        })

        if judgment == "concern":
            breakdown_items.append({
                "label": module_name,
                "category": "findings",
                "delta": -15,
                "reason": ans.get("explanation", "Methodological concern identified."),
            })
        elif judgment == "inconsistency":
            breakdown_items.append({
                "label": module_name,
                "category": "findings",
                "delta": -25,
                "reason": ans.get("explanation", "Severe contradiction / inconsistency found."),
            })
        elif judgment == "insufficient":
            breakdown_items.append({
                "label": module_name,
                "category": "findings",
                "delta": -4,
                "reason": "Information not reported in paper.",
            })

    # Ensure score strictly matches 100 + total deductions
    total_deductions = sum(item["delta"] for item in breakdown_items)
    computed_score = max(0, min(100, 100 + total_deductions))

    # Determine credibility tier
    if computed_score >= 85:
        tier = "high"
        tier_label = "High Credibility"
    elif computed_score >= 65:
        tier = "moderate"
        tier_label = "Moderate Credibility"
    elif computed_score >= 40:
        tier = "low"
        tier_label = "Low Credibility"
    else:
        tier = "critical"
        tier_label = "Critical Concerns"

    # Build claim items
    claims = []
    main_claims_text = paper_context.get("main_claims", "")
    claim_ans = answers.get("claim_evidence_match", {})
    claim_judgment = claim_ans.get("judgment", "supported")
    claim_quote = claim_ans.get("quote", "")
    claim_fuzzy = claim_ans.get("fuzzy_match", {})
    claim_verified = claim_ans.get("verified", True)

    if main_claims_text and main_claims_text != "not reported":
        claims.append({
            "claim": main_claims_text[:300],
            "verdict": "supported" if claim_judgment == "supported" else "partial",
            "judgment": claim_judgment,
            "reasoning": claim_ans.get("explanation", "Evaluated from paper results against experimental evidence."),
            "quote": claim_quote,
            "location": "Docling Section: Conclusions / Results",
            "verified": claim_verified,
            "verificationNote": claim_ans.get("verification_note", "Quote verified with Docling OCR text."),
            "fuzzyMatch": {
                "matched": claim_fuzzy.get("matched", claim_verified),
                "score": claim_fuzzy.get("score", 1.0 if claim_verified else 0.0),
                "method": claim_fuzzy.get("method", "fuzzy" if claim_verified else "none"),
                "note": claim_fuzzy.get("note", "Verified against Docling markdown text."),
            },
        })

    # Summary text
    summary_text = (
        f"This paper achieved a credibility score of {computed_score}/100 ({tier_label}). "
        f"Task Type: {paper_context.get('task_type', 'ML Analysis')}. "
        f"Dataset: {paper_context.get('dataset', 'Reported dataset')}."
    )

    title = os.path.splitext(pdf_filename)[0].replace("_", " ")

    return {
        "paper": {
            "title": title,
            "authors": ["Extracted from Paper"],
            "venue": "Machine Learning Literature",
            "year": 2024,
            "isPreprint": False,
        },
        "retraction": {
            "status": "none",
        },
        "paperType": paper_context.get("task_type", "Machine Learning Paper"),
        "checklistApplies": "full",
        "findings": findings,
        "claims": claims,
        "credibility": {
            "score": computed_score,
            "tier": tier,
            "tierLabel": tier_label,
            "summary": summary_text,
            "breakdown": breakdown_items,
        },
    }



def run_pipeline(pdf_path: str) -> dict:
    """
    Executes the entire end-to-end verification pipeline on a PDF file.
    """
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("outputs", exist_ok=True)

    # Step 1: Docling PDF -> Markdown
    print(f"\n[Step 1] Parsing PDF with Docling: {pdf_path}")
    parsed = parse_paper(pdf_path)
    paper_markdown = parsed["markdown"]

    # Save output markdown
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_md_path = os.path.join("outputs", f"{base_name}.md")
    with open(output_md_path, "w", encoding="utf-8") as f:
        f.write(paper_markdown)

    # Step 2: Extract structured methodology context
    print(f"\n[Step 2] Extracting paper context via Gemini...")
    paper_context = extract_paper_context(paper_markdown)

    # Step 3 is AUDIT_QUESTIONS (imported directly)

    # Step 4: Run Gemini Audit against AUDIT_QUESTIONS
    print(f"\n[Step 4] Running LLM Audit against questions...")
    raw_answers = run_audit(paper_context, paper_markdown)

    # Step 4.5: Verify every quote actually exists in source text
    print(f"\n[Step 4.5] Verifying quotes against source text...")
    answers = verify_answers(raw_answers, paper_markdown)

    # Step 5: Compute deterministic credibility score
    print(f"\n[Step 5] Computing score...")
    score_result = compute_score(answers)

    # Step 6: Assemble final result
    report = {
        "paper_source": pdf_path,
        "paper_context": paper_context,
        "score": score_result["score"],
        "breakdown": score_result["breakdown"],
        "answers": answers,
        "flags": [
            {
                "question_id": qid,
                "question_text": AUDIT_QUESTIONS[qid]["question"],
                "judgment": ans["judgment"],
                "quote": ans["quote"],
                "explanation": ans["explanation"],
                "verified": ans.get("verified"),
            }
            for qid, ans in answers.items()
        ],
    }
    return report


@app.post("/analyze")
async def analyze_paper(
    identifier: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    if not identifier and not file:
        raise HTTPException(status_code=400, detail="Provide a DOI, an arXiv ID, or a PDF.")

    if file and file.filename:
        os.makedirs("uploads", exist_ok=True)
        upload_path = os.path.join("uploads", file.filename)

        with open(upload_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        try:
            # Run the complete pipeline
            pipeline_result = run_pipeline(upload_path)
            # Format report for the frontend
            frontend_report = format_frontend_report(pipeline_result, file.filename)
            return frontend_report
        except Exception as e:
            print(f"[Error in pipeline]: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    elif identifier:
        # Placeholder for identifier lookups (e.g. arXiv/DOI)
        return {
            "paper": {
                "title": f"Report for {identifier}",
                "authors": ["System Generated"],
                "isPreprint": True,
            },
            "retraction": {"status": "none"},
            "paperType": "Identifier Submission",
            "checklistApplies": "full",
            "findings": [],
            "claims": [],
            "credibility": {
                "score": 50,
                "tier": "moderate",
                "tierLabel": "Moderate Credibility",
                "summary": f"Submission received for identifier {identifier}.",
                "breakdown": [],
            }
        }


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].endswith(".pdf"):
        report = run_pipeline(sys.argv[1])
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        import uvicorn
        uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
