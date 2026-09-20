"""
Step 3: The fixed list of audit questions.

Loads the checklist questions from AUDIT_QUESTIONS.JSON if available,
with a built-in fallback.
"""

import os
import json

_JSON_PATH = os.path.join(os.path.dirname(__file__), "AUDIT_QUESTIONS.JSON")

if os.path.exists(_JSON_PATH):
    try:
        with open(_JSON_PATH, "r", encoding="utf-8") as f:
            AUDIT_QUESTIONS = json.load(f)
    except Exception:
        AUDIT_QUESTIONS = {}
else:
    AUDIT_QUESTIONS = {}

if not AUDIT_QUESTIONS:
    AUDIT_QUESTIONS = {
        "data_preprocessing": {
            "question": "Are the dataset, preprocessing steps, and data preparation procedures appropriate for the stated task and sufficiently described to assess them?"
        },
        "leakage": {
            "question": "Is there any indication that information from the test/evaluation data, or information unavailable at prediction time, influenced model training or development?"
        },
        "evaluation": {
            "question": "Are the reported metrics and evaluation protocol appropriate for the research objective, task, and relevant characteristics of the data?"
        },
        "statistical_analysis": {
            "question": "Are the statistical methods and uncertainty or significance analyses appropriate for the study design, data, and research question?"
        },
        "baseline_fairness": {
            "question": "Are the proposed method and comparison methods evaluated under comparable conditions, including data, preprocessing, and evaluation protocol?"
        },
        "claim_evidence_match": {
            "question": "Do the scope and strength of the paper's main claims match what the reported experiments and results actually establish?"
        },
        "reporting_sufficiency": {
            "question": "Is enough information reported to assess the data, preprocessing, leakage risk, statistical analysis, evaluation, and claim-evidence alignment?"
        },
    }

