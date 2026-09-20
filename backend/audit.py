"""
Step 4: Answer each question in AUDIT_QUESTIONS using:
  - the extracted paper_context dict (from extract.py)
  - the raw paper markdown (for pulling exact quotes as evidence)

Input:
    paper_context (dict, from extract.py)
    paper_markdown (str)

Output:
    dict keyed by question id ->
        {
            "question_id": ...,
            "judgment": ...,
            "quote": ...,
            "explanation": ...
        }

judgment is always one of:
    "supported" | "concern" | "insufficient" | "inconsistency"
"""

import os
import sys
import glob
import json

from dotenv import load_dotenv, find_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from questions import AUDIT_QUESTIONS


# ============================================================
# 1. LOAD ENVIRONMENT
# ============================================================

load_dotenv(find_dotenv())
load_dotenv(".env")
load_dotenv("../.env")
load_dotenv(".env.local")
load_dotenv("../.env.local")


# ============================================================
# 2. GEMINI CONFIGURATION
# ============================================================

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

JUDGMENTS = [
    "supported",
    "concern",
    "insufficient",
    "inconsistency",
]


# ============================================================
# 3. OUTPUT SCHEMA
# ============================================================

class AuditAnswer(BaseModel):
    question_id: str = Field(
        description="The ID of the audit question being answered."
    )

    judgment: str = Field(
        description=(
            "One of: supported, concern, insufficient, inconsistency"
        )
    )

    quote: str = Field(
        description=(
            "Exact sentence or sentences from the paper supporting "
            "the judgment. Empty string if judgment is insufficient."
        )
    )

    explanation: str = Field(
        description="One or two sentences explaining the judgment."
    )


class AuditResult(BaseModel):
    answers: list[AuditAnswer]


# ============================================================
# 4. CREATE GEMINI CLIENT
# ============================================================

def get_gemini_client():
    """
    Create Gemini client using GEMINI_API_KEY from .env.
    """
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY not found.\n"
            "Add it to your .env file:\n\n"
            "GEMINI_API_KEY=your_key_here"
        )

    return genai.Client(api_key=api_key)


# ============================================================
# 5. RUN AUDIT
# ============================================================

from cache import cached, get_hash

def run_audit(
    paper_context: dict,
    paper_markdown: str,
    client=None,
) -> dict:
    if client is None:
        client = get_gemini_client()

    cache_key = (
        "audit_v1",
        MODEL,
        get_hash(json.dumps(paper_context, sort_keys=True)),
        get_hash(paper_markdown),
    )

    def _call():
        # --------------------------------------------------------
        # Build questions
        # --------------------------------------------------------
        questions_block = "\n".join(
            f'- id="{qid}": {q["question"]}'
            for qid, q in AUDIT_QUESTIONS.items()
        )

        system_instruction = """
You are auditing the methodology of an ML research paper.

You are given:
1. A structured summary extracted from the paper.
2. The complete paper text.
3. A set of audit questions.

Answer EVERY audit question using ONLY information explicitly present in the supplied paper.
Do not use outside knowledge. Do not guess.

JUDGMENT RULES:
"supported": The paper clearly provides evidence that the methodology handles the issue correctly.
"concern": There is evidence suggesting a genuine methodological problem or weakness.
"insufficient": The paper does not report enough information to determine whether the issue is handled correctly.
"inconsistency": The paper contains a clear internal contradiction or methodological error.

EVIDENCE RULES:
Every judgment except "insufficient" MUST contain an exact quote from the paper.
For "insufficient", use an empty string for quote.
Keep explanations to one or two sentences.
Return one answer for EVERY audit question.
"""

        user_content = f"""
STRUCTURED PAPER CONTEXT
========================
{json.dumps(paper_context, indent=2, ensure_ascii=False)}

AUDIT QUESTIONS
===============
{questions_block}

COMPLETE PAPER TEXT
===================
{paper_markdown}
"""

        print("\nSending paper to Gemini for audit...")
        print(f"Paper length: {len(paper_markdown):,} characters")
        print(f"Number of questions: {len(AUDIT_QUESTIONS)}")

        response = client.models.generate_content(
            model=MODEL,
            contents=user_content,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=AuditResult,
                temperature=0,
            ),
        )

        if response.parsed is not None:
            if isinstance(response.parsed, AuditResult):
                result = response.parsed.model_dump()
            elif isinstance(response.parsed, BaseModel):
                result = response.parsed.model_dump()
            else:
                result = response.parsed
        elif response.text:
            result = json.loads(response.text)
        else:
            raise RuntimeError("Gemini returned neither parsed output nor text.")

        answers_list = result.get("answers", [])
        answers = {
            answer["question_id"]: answer
            for answer in answers_list
        }

        # Validate question coverage
        expected_ids = set(AUDIT_QUESTIONS.keys())
        returned_ids = set(answers.keys())
        missing = expected_ids - returned_ids
        if missing:
            print("\nWARNING: Gemini did not answer these questions:")
            for qid in sorted(missing):
                print(f"  - {qid}")

        return answers

    return cached(cache_key, _call)



# ============================================================
# 6. COMMAND LINE ENTRY POINT
# ============================================================

if __name__ == "__main__":
    from pdf_parser import parse_paper
    from extract import extract_paper_context



    if len(sys.argv) < 2:
        print("Usage:")
        print("python audit.py <path_to_pdf_or_markdown>")
        sys.exit(1)

    input_path = sys.argv[1]

    # --------------------------------------------------------
    # Step 1: Parse or Read Markdown
    # --------------------------------------------------------
    if input_path.lower().endswith(".pdf"):
        print("\n" + "=" * 60)
        print("STEP 1: PARSING PDF WITH DOCLING")
        print("=" * 60)
        parsed = parse_paper(input_path)
        paper_markdown = parsed["markdown"]
    else:
        print("\n" + "=" * 60)
        print(f"STEP 1: READING MARKDOWN FROM {input_path}")
        print("=" * 60)
        with open(input_path, "r", encoding="utf-8") as f:
            paper_markdown = f.read()

    # --------------------------------------------------------
    # Step 2: Extract structured context
    # --------------------------------------------------------
    print("\n" + "=" * 60)
    print("STEP 2: EXTRACTING PAPER CONTEXT")
    print("=" * 60)

    context = extract_paper_context(paper_markdown)

    # --------------------------------------------------------
    # Step 3: Audit the paper
    # --------------------------------------------------------
    print("\n" + "=" * 60)
    print("STEP 3: RUNNING AUDIT")
    print("=" * 60)

    answers = run_audit(
        paper_context=context,
        paper_markdown=paper_markdown,
    )

    # --------------------------------------------------------
    # Step 4: Print results
    # --------------------------------------------------------
    print("\n" + "=" * 60)
    print("FINAL AUDIT")
    print("=" * 60)

    print(
        json.dumps(
            answers,
            indent=2,
            ensure_ascii=False
        )
    )
