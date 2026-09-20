# 📑 Paper Check

> **Automated ML Research Methodology & Credibility Auditor**  
> Fast, grounded auditing for machine learning papers with anti-hallucination quote verification and deterministic credibility scoring.

---

## 🚀 Overview

**Paper Check** is an intelligent assistant that reviews machine learning research papers against strict methodological checklists (REFORMS guidelines, data leakage risks, evaluation protocol rigor, and claim-evidence alignment).

Unlike generic LLM wrappers, **Paper Check** uses a deterministic multi-stage pipeline:
1. **Document Conversion**: Extracts structured text and tables from PDFs with [Docling](https://github.com/DS4SD/docling).
2. **Context Extraction**: Gathers structured methodology parameters (datasets, data splits, baselines, metrics, preprocessing).
3. **Checklist Audit**: Evaluates the paper against 7 rigorous research questions requiring verbatim evidence quotes.
4. **Anti-Hallucination Verification**: Deterministically searches the source document to verify that claimed evidence quotes actually exist. Hallucinated quotes are immediately flagged and downgraded.
5. **Credibility Scoring**: Generates an explainable 0–100 credibility score with point breakdowns and actionable flags.

---

## 🏗️ Architecture & Pipeline

```
                     ┌──────────────────┐
                     │   PDF Document   │
                     └─────────┬────────┘
                               │
                               ▼ [Docling / PyPdfium Backend]
                     ┌──────────────────┐
                     │ Structured MD    │
                     └─────────┬────────┘
                               │
                               ▼ [extract.py: Section-wise extraction]
                     ┌──────────────────┐
                     │  Paper Context   │
                     └─────────┬────────┘
                               │
             ┌─────────────────┴─────────────────┐
             │                                   │
             ▼                                   ▼
    ┌──────────────────┐               ┌──────────────────┐
    │ AUDIT_QUESTIONS  │               │ Raw Markdown Doc │
    └────────┬─────────┘               └────────┬─────────┘
             │                                   │
             └─────────────────┬─────────────────┘
                               │
                               ▼ [audit.py: Gemini 2.5 Flash]
                     ┌──────────────────┐
                     │ Raw Audit Answers│ (with evidence quotes)
                     └─────────┬────────┘
                               │
                               ▼ [verify.py: Deterministic Substring & Fuzzy Match]
                     ┌──────────────────┐
                     │ Verified Answers │ (hallucinated quotes downgraded)
                     └─────────┬────────┘
                               │
                               ▼ [score.py]
                     ┌──────────────────┐
                     │ Credibility Score│ (0-100 & point breakdown)
                     └─────────┬────────┘
                               │
                               ▼ [FastAPI -> Next.js Frontend]
                     ┌──────────────────┐
                     │ Interactive UI   │
                     └──────────────────┘
```

---

## ✨ Features

- **📑 Native PDF Extraction**: High-fidelity conversion preserving headings, hierarchy, and tables.
- **🛡️ Anti-Hallucination Evidence Verification**: Evaluates answers with strict quote-matching against the raw paper text.
- **📊 7-Point Methodology Audit**:
  1. `data_preprocessing`: Dataset, preparation, and cleaning appropriateness.
  2. `leakage`: Temporal, spatial, or feature leakage between train and test distributions.
  3. `evaluation`: Alignment between metrics, task objectives, and class distributions.
  4. `statistical_analysis`: Significance tests, variance, confidence intervals, and error bars.
  5. `baseline_fairness`: Equal tuning and evaluation conditions across comparisons.
  6. `claim_evidence_match`: Matching conclusions and claim strength to experimental evidence.
  7. `reporting_sufficiency`: Reproducibility and parameter disclosure.
- **🎯 Explainable Credibility Score**: 0–100 score categorized into **High**, **Moderate**, **Low**, and **Critical Concerns**.
- **💻 Modern Next.js Dashboard**: Dark-mode interface with meter graphics, evidence inspection, and finding badges.

---

## 🛠️ Tech Stack

- **Frontend**: Next.js 15 (App Router), React 19, TypeScript, Vanilla CSS
- **Backend**: Python 3.11+, FastAPI, Uvicorn, Pydantic v2
- **Document Parser**: IBM Docling (`docling`, `pypdfium2`)
- **LLM / AI**: Google Gemini API (`google-genai`, `gemini-2.5-flash`)

---

## ⚡ Getting Started

### 1. Prerequisites
- **Node.js** (v18+)
- **Python** (v3.11 - v3.13)
- **Google Gemini API Key** (Get free key from [Google AI Studio](https://aistudio.google.com/app/apikey))

---

### 2. Backend Setup

```powershell
# Navigate to the backend directory
cd backend

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1  # On Windows
# source venv/bin/activate   # On macOS/Linux

# Install dependencies
pip install fastapi uvicorn python-multipart docling google-genai python-dotenv pydantic
```

Create a `.env` file in the root or `backend/` directory:
```env
GEMINI_API_KEY=AIzaSy...your_gemini_api_key_here
```

Start the backend API server:
```powershell
python main.py
```
*The FastAPI backend will start at `http://127.0.0.1:8000`.*

---

### 3. Frontend Setup

From the project root:

```powershell
# Install Node dependencies
npm install

# Start the development server
npm run dev
```

*The Next.js frontend will be live at `http://localhost:3000`.*

---

## 🧪 CLI Standalone Usage

You can also run analysis steps directly from the command line without the web UI:

```powershell
# Run the complete pipeline on a PDF:
python backend/main.py backend/uploads/MAINPAPER.pdf

# Run extraction on a Markdown file:
python backend/extract.py backend/outputs/MAINPAPER.md

# Verify answers against raw paper text:
python backend/verify.py backend/outputs/answers.json backend/outputs/MAINPAPER.md
```

---

## 📄 License

MIT License. Built for rigorous ML paper auditing and reproducibility.
