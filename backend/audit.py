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
from groq import Groq
from pydantic import BaseModel, Field

load_dotenv(find_dotenv())
load_dotenv(".env")
load_dotenv("../.env")
load_dotenv(".env.local")
load_dotenv("../.env.local")

GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

JUDGMENTS = [
    "supported",
    "concern",
    "insufficient",
    "inconsistency",
]

def load_audit_questions():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(base_dir, "AUDIT_QUESTIONS.JSON")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data

class AuditAnswer(BaseModel):
    question_id: str = Field(description="The ID of the audit question being answered.")
    judgment: str = Field(description="One of: supported, concern, insufficient, inconsistency")
    quote: str = Field(description="Exact sentence(s) from the paper. Empty string if insufficient.")
    explanation: str = Field(description="One or two sentences explaining the judgment.")

def get_groq_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found. Add it to your .env file.")
    return Groq(api_key=api_key)

def _extract_json_from_text(text: str):
    text = text.strip()

    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:].strip()
        text = text.strip()

    return json.loads(text)

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

def run_single_question(client, question_id: str, question: str, paper_context: dict, paper_markdown: str):
    relevant_excerpt = get_relevant_paper_excerpt(question_id, paper_markdown)

    system_instruction = """
You are auditing one methodology question from an ML research paper.

Use ONLY information explicitly present in the supplied excerpt.
Do not use outside knowledge, guess, or assume standard practices.

Judgments:
- supported
- concern
- insufficient
- inconsistency

Missing information alone must be classified as insufficient.

For every judgment except insufficient, provide an exact verbatim quote
from the paper. For insufficient, quote must be an empty string.
Keep the explanation to one or two sentences.
Return valid JSON only.
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
            completion = client.chat.completions.create(
                model=GROQ_MODEL,
                temperature=0,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_content},
                ],
            )

            content = completion.choices[0].message.content
            data = _extract_json_from_text(content)

            if "question_id" not in data:
                data["question_id"] = question_id

            return data

        except Exception as e:
            err = str(e).lower()
            if "rate limit" in err or "429" in err or "too many requests" in err:
                wait_time = (attempt + 1) * 10
                print(f"Rate limit for {question_id}. Waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
            raise

    raise RuntimeError(f"Failed to answer audit question {question_id} after retries")

def run_audit(paper_context: dict, paper_markdown: str, client=None) -> dict:
    if client is None:
        client = get_groq_client()

    AUDIT_QUESTIONS = load_audit_questions()
    answers = {}

    print("\nRunning one Groq request per audit question...")
    print(f"Paper length: {len(paper_markdown):,} characters")
    print(f"Number of questions: {len(AUDIT_QUESTIONS)}")

    for index, (question_id, question_data) in enumerate(AUDIT_QUESTIONS.items(), start=1):
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

if __name__ == "__main__":
    from pdf_parser import parse_paper
    from extract import extract_paper_context

    if len(sys.argv) < 2:
        print("Usage:")
        print("python audit.py <path_to_pdf_or_markdown>")
        sys.exit(1)

    input_path = sys.argv[1]

    if input_path.lower().endswith(".pdf"):
        parsed = parse_paper(input_path)
        paper_markdown = parsed["markdown"]
    else:
        with open(input_path, "r", encoding="utf-8") as f:
            paper_markdown = f.read()

    context = extract_paper_context(paper_markdown)
    answers = run_audit(paper_context=context, paper_markdown=paper_markdown)

    print(json.dumps(answers, indent=2, ensure_ascii=False))
