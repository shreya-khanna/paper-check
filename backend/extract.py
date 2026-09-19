"""
Step 2: Extract structured methodology information from a Docling Markdown paper.

Input:
    parsed["markdown"] from docling_parse.py

Output:
    A fixed dictionary containing the methodology information we want
    for every paper.

Pipeline:
    PDF
      ↓
    Docling
      ↓
    Markdown
      ↓
    Section-wise splitting
      ↓
    Gemini extraction for each section
      ↓
    Merge into one dictionary
"""

import json
import re
from google import genai
from google.genai import types


# ============================================================
# 1. GEMINI CONFIGURATION
# ============================================================

MODEL = "gemini-2.5-flash"


# ============================================================
# 2. FINAL MVP SCHEMA
# ============================================================

EXTRACTION_FIELDS = [
    "task_type",
    "dataset",
    "data_split",
    "preprocessing",
    "method",
    "baselines",
    "metrics",
    "results",
    "main_claims",
    "limitations",
]


# Gemini structured output schema
EXTRACTION_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "task_type": {"type": "STRING"},
        "dataset": {"type": "STRING"},
        "data_split": {"type": "STRING"},
        "preprocessing": {"type": "STRING"},
        "method": {"type": "STRING"},
        "baselines": {"type": "STRING"},
        "metrics": {"type": "STRING"},
        "results": {"type": "STRING"},
        "main_claims": {"type": "STRING"},
        "limitations": {"type": "STRING"},
    },
    "required": EXTRACTION_FIELDS,
}


# ============================================================
# 3. EMPTY DICTIONARY
# ============================================================

def empty_extraction():
    """
    Creates the same dictionary shape for every paper.
    """

    return {
        "task_type": "not reported",
        "dataset": "not reported",
        "data_split": "not reported",
        "preprocessing": "not reported",
        "method": "not reported",
        "baselines": "not reported",
        "metrics": "not reported",
        "results": "not reported",
        "main_claims": "not reported",
        "limitations": "not reported",
    }


# ============================================================
# 4. SPLIT DOC LING MARKDOWN INTO SECTIONS
# ============================================================

def split_into_sections(markdown: str):
    """
    Splits Docling Markdown using Markdown headings.

    Example:

        # Introduction
        text...

        ## Dataset
        text...

        ## Method
        text...

    becomes:

        [
            ("Introduction", "text..."),
            ("Dataset", "text..."),
            ("Method", "text...")
        ]

    We keep ALL text. Nothing is truncated.
    """

    # Matches Markdown headings:
    # # Heading
    # ## Heading
    # ### Heading
    heading_pattern = re.compile(
        r"^(#{1,6})\s+(.+?)\s*$",
        re.MULTILINE
    )

    matches = list(heading_pattern.finditer(markdown))

    # If Docling produced no headings, treat the whole paper
    # as one section.
    if not matches:
        return [("Full Paper", markdown)]

    sections = []

    # Text before the first heading
    if matches[0].start() > 0:
        intro = markdown[:matches[0].start()].strip()

        if intro:
            sections.append(("Before First Heading", intro))

    for i, match in enumerate(matches):

        section_title = match.group(2).strip()

        start = match.end()

        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            end = len(markdown)

        section_text = markdown[start:end].strip()

        if section_text:
            sections.append((section_title, section_text))

    return sections


# ============================================================
# 5. EXTRACT ONE SECTION WITH GEMINI
# ============================================================

def extract_section(section_title: str, section_text: str, client):
    """
    Ask Gemini to extract information from ONE section.

    Gemini returns the same schema every time.
    """

    system_instruction = """
You are extracting factual information from an ML research paper.

Read ONLY the supplied paper section.

Fill the predefined fields with information explicitly stated
in this section.

Do not guess or infer information.

If a field is not mentioned in this section, write:
"not reported"

Keep answers concise.

For example:
- Do not explain what a dataset is.
- Do not explain what accuracy means.
- Just extract the information stated by the authors.
"""

    prompt = f"""
Paper section: {section_title}

Section content:
----------------
{section_text}
----------------

Extract the relevant information into the predefined schema.

Remember:
- Only use information explicitly present in this section.
- Fields unrelated to this section should be "not reported".
"""

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=EXTRACTION_SCHEMA,
            temperature=0,
        ),
    )

    return json.loads(response.text)


# ============================================================
# 6. MERGE SECTION EXTRACTIONS
# ============================================================

def merge_extractions(section_results):
    """
    Combine the information extracted from all sections.

    If multiple sections contain information for the same field,
    concatenate the useful information rather than throwing it away.
    """

    final = empty_extraction()

    for result in section_results:

        for field in EXTRACTION_FIELDS:

            value = result.get(field, "not reported")

            if not value or value == "not reported":
                continue

            # Nothing has been extracted for this field yet
            if final[field] == "not reported":
                final[field] = value

            # Additional information was found in another section
            else:
                if value not in final[field]:
                    final[field] += "; " + value

    return final


# ============================================================
# 7. MAIN EXTRACTION FUNCTION
# ============================================================

def extract_paper_context(paper_markdown: str, client=None):
    """
    Takes the COMPLETE Docling Markdown and extracts information
    section by section.

    No arbitrary character truncation is performed.
    """

    if client is None:
        client = genai.Client()

    sections = split_into_sections(paper_markdown)

    print(f"Found {len(sections)} sections.")

    section_results = []

    for i, (title, text) in enumerate(sections):

        print(f"Extracting section {i + 1}/{len(sections)}: {title}")

        result = extract_section(
            section_title=title,
            section_text=text,
            client=client,
        )

        section_results.append(result)

    final_context = merge_extractions(section_results)

    return final_context


# ============================================================
# 8. RUN FROM COMMAND LINE
# ============================================================

if __name__ == "__main__":

    import sys

    from docling_parse import parse_paper

    if len(sys.argv) < 2:
        print("Usage: python extract.py <path_to_pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]

    # -------------------------
    # Step 1: PDF → Markdown
    # -------------------------

    parsed = parse_paper(pdf_path)

    markdown = parsed["markdown"]

    # -------------------------
    # Step 2: Markdown → JSON
    # -------------------------

    context = extract_paper_context(markdown)

    # -------------------------
    # Print final result
    # -------------------------

    print("\nFinal extraction:\n")

    print(
        json.dumps(
            context,
            indent=2,
            ensure_ascii=False
        )
    )