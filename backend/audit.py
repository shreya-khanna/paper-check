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
import json
import re
import time

from dotenv import load_dotenv, find_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# ============================================================
# 1. LOAD ENVIRONMENT
# ============================================================

load_dotenv(find_dotenv())
load_dotenv(".env")
load_dotenv("../.env")
load_dotenv(".env.local")
load_dotenv("../.env.local")

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

JUDGMENTS = [
    "supported",
    "concern",
    "insufficient",
    "inconsistency",
]


# ============================================================
# 2. READ QUESTIONS FROM JSON
# ============================================================

def load_audit_questions():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(base_dir, "AUDIT_QUESTIONS.JSON")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data


# ============================================================
# 3. OUTPUT SCHEMA
# ============================================================

class AuditAnswer(BaseModel):
    question_id: str = Field(
        description="The ID of the audit question being answered."
    )
    judgment: str = Field(
        description="One of: supported, concern, insufficient, inconsistency"
    )
    quote: str = Field(
        description=(
            "Exact sentence or sentences from the paper supporting the judgment. "
            "Empty string if judgment is insufficient."
        )
    )
    explanation: str = Field(
        description="One or two sentences explaining the judgment."
    )


# ============================================================
# 4. CREATE GEMINI CLIENT
# ============================================================

def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY not found.\n"
            "Add it to your .env file:\n\n"
            "GEMINI_API_KEY=your_key_here"
        )
    return genai.Client(api_key=api_key)


# ============================================================
# 5. SECTION SELECTION FOR RELEVANT PAPER EXCERPTS
# ============================================================

QUESTION_SECTION_HINTS = {
    "q1_population_scope": [
        "population", "participants", "study population", "sample",
        "setting", "inclusion", "recruitment", "distribution"
    ],
    "q2_ml_motivation": [
        "introduction", "motivation", "background", "objective",
        "problem formulation", "machine learning", "ml"
    ],
    "q3_data_sources": [
        "dataset", "data collection", "data source", "annotation",
        "labeling", "training data", "evaluation data"
    ],
    "q4_sampling_representativeness": [
        "sampling", "sample", "population", "distribution", "representativeness",
        "frame", "inclusion"
    ],
    "q5_reproducibility": [
        "reproducibility", "code", "software", "implementation",
        "resources", "hardware", "infrastructure", "availability"
    ],
    "q6_preprocessing": [
        "methods", "preprocessing", "data cleaning", "missing data",
        "normalization", "filtering", "exclusion", "feature engineering"
    ],
    "q7_modeling_details": [
        "methods", "model", "architecture", "training", "hyperparameters",
        "validation", "selection", "baseline"
    ],
    "q8_baselines_and_evaluation": [
        "evaluation", "results", "baseline", "validation", "split",
        "cross-validation", "test set", "performance"
    ],
    "q9_leakage": [
        "validation", "train", "test", "data leakage", "preprocessing",
        "feature selection", "duplicates", "contamination"
    ],
    "q10_metrics_uncertainty": [
        "metrics", "results", "uncertainty", "confidence interval",
        "standard deviation", "statistics", "significance", "test"
    ],
    "q11_claims_generalizability": [
        "conclusion", "discussion", "limitations", "generalizability",
        "external validity", "results", "findings"
    ],
}

def split_markdown_into_sections(markdown: str):
    """
    Split markdown into (heading, text) sections using headings.
    """
    sections = []
    blocks = re.split(r"(?m)^(#{1,6})\\s+", markdown)

    if len(blocks) <= 1:
        return [("document", markdown)]

    for i in range(1, len(blocks), 2):
        heading = blocks[i].strip()
        body = blocks[i + 1].strip() if i + 1 < len(blocks) else ""
        if heading:
            sections.append((heading, body))

    return sections

def get_relevant_paper_excerpt(question_id: str, paper_markdown: str, max_chars: int = 12000):
    sections = split_markdown_into_sections(paper_markdown)
    hints = QUESTION_SECTION_HINTS.get(question_id, [])

    selected = []
    for heading, text in sections:
        heading_lower = heading.lower()
        text_lower = text.lower()
        score = 0

        for hint in hints:
            h = hint.lower()
            if h in heading_lower or h in text_lower:
                score += 1

        if score > 0:
            selected.append((score, heading, text))

    if not selected:
        return paper_markdown[:max_chars]

    selected.sort(key=lambda x: x[0], reverse=True)
    excerpt_parts = []

    for _, heading, text in selected[:4]:
        excerpt_parts.append(f"## {heading}\n{text}")

    excerpt = "\n\n".join(excerpt_parts)
    if len(excerpt) > max_chars:
        excerpt = excerpt[:max_chars]

    return excerpt


# ============================================================
# 6. RUN AUDIT
# ============================================================

def run_single_question(
    client,
    question_id: str,
    question: str,
    paper_context: dict,
    paper_markdown: str,
):
    relevant_excerpt = get_relevant_paper_excerpt(question_id, paper_markdown)

    system_instruction = """
You are auditing one methodology question from an ML research paper.

Use ONLY information explicitly present in the supplied excerpt.
Do not use outside knowledge, guess, or assume standard practices.

Judgments:
- supported: the paper clearly provides evidence that the issue is handled correctly
- concern: the paper provides evidence of a methodological weakness
- insufficient: the paper does not provide enough information
- inconsistency: the paper contains a clear internal contradiction or mismatch

Missing information alone must be classified as insufficient.

For every judgment except insufficient, provide an exact verbatim quote
from the paper. For insufficient, quote must be an empty string.
Keep the explanation to one or two sentences.
"""

    user_content = f"""
STRUCTURED PAPER CONTEXT
========================
{json.dumps(paper_context, indent=2, ensure_ascii=False)}

AUDIT QUESTION
==============
Question ID: {question_id}
Question: {question}

RELEVANT PAPER EXCERPT
======================
{relevant_excerpt}
"""

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=AuditAnswer,
                    temperature=0,
                ),
            )

            if response.parsed is not None:
                if isinstance(response.parsed, BaseModel):
                    return response.parsed.model_dump()
                return response.parsed

            if response.text:
                return json.loads(response.text)

            raise RuntimeError(f"Empty response for audit question {question_id}")

        except Exception as e:
            error = str(e)

            if "429" in error or "RESOURCE_EXHAUSTED" in error:
                wait_time = (attempt + 1) * 10
                print(f"Rate limit for {question_id}. Waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise

    raise RuntimeError(
        f"Failed to answer audit question {question_id} after retries"
    )


def run_audit(paper_context: dict, paper_markdown: str, client=None) -> dict:
    if client is None:
        client = get_gemini_client()

    AUDIT_QUESTIONS = load_audit_questions()
    answers = {}

    print("\nRunning one Gemini request per audit question...")
    print(f"Paper length: {len(paper_markdown):,} characters")
    print(f"Number of questions: {len(AUDIT_QUESTIONS)}")

    for index, (question_id, question_data) in enumerate(
        AUDIT_QUESTIONS.items(),
        start=1,
    ):
        print(f"[{index}/{len(AUDIT_QUESTIONS)}] Auditing {question_id}...")

        answer = run_single_question(
            client=client,
            question_id=question_id,
            question=question_data["question"],
            paper_context=paper_context,
            paper_markdown=paper_markdown,
        )

        answer["question_id"] = question_id
        answers[question_id] = answer

    return answers


# ============================================================
# 7. COMMAND LINE ENTRY POINT
# ============================================================

if __name__ == "__main__":
    from pdf_parser import parse_paper
    from extract import extract_paper_context

    if len(sys.argv) < 2:
        print("Usage:")
        print("python audit.py <path_to_pdf_or_markdown>")
        sys.exit(1)

    input_path = sys.argv[1]

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

    print("\n" + "=" * 60)
    print("STEP 2: EXTRACTING PAPER CONTEXT")
    print("=" * 60)
    context = extract_paper_context(paper_markdown)

    print("\n" + "=" * 60)
    print("STEP 3: RUNNING AUDIT")
    print("=" * 60)
    answers = run_audit(
        paper_context=context,
        paper_markdown=paper_markdown,
    )

    print("\n" + "=" * 60)
    print("FINAL AUDIT")
    print("=" * 60)
    print(json.dumps(answers, indent=2, ensure_ascii=False))
