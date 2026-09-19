import type { Report } from "./types";

// Demo data only. Not a real paper. Replace with your backend's output.
export const sampleReport: Report = {
  paper: {
    title: "Sample paper: A deep learning model for early sepsis detection",
    authors: ["A. Author", "B. Author", "C. Author"],
    venue: "Example Journal of Medical AI",
    year: 2024,
    doi: "10.0000/example.12345",
    isPreprint: false,
  },
  retraction: { status: "none" },
  paperType: "Machine learning, binary classification",
  checklistApplies: "full",
  findings: [
    {
      id: "goal-1",
      module: "Study goals",
      question: "Is the scientific claim stated, and is it one the study design can test?",
      status: "pass",
      note: "The main claim is stated in the abstract and matches a prediction task.",
    },
    {
      id: "repro-1",
      module: "Computational reproducibility",
      question: "Are code and data available?",
      status: "not_reported",
      note: "No code or data availability statement was found in the paper.",
    },
    {
      id: "data-1",
      module: "Data quality",
      question: "Are class counts reported, and is the dataset imbalanced?",
      status: "pass",
      note: "Positive cases are about 4% of the dataset.",
      quote: "Of 48,210 patient stays, 1,930 developed sepsis.",
      location: "Section 3.1, p. 4",
    },
    {
      id: "prep-1",
      module: "Data preprocessing",
      question: "If the data is imbalanced, was it handled, and after the train/test split?",
      status: "flag",
      note: "Oversampling appears to be applied before the split, which can leak test examples into training.",
      quote: "We balanced the dataset using SMOTE and then split it 80/20 for training and testing.",
      location: "Section 3.3, p. 5",
    },
    {
      id: "leak-1",
      module: "Data leakage",
      question: "Could information from the test set have reached training?",
      status: "flag",
      note: "Follows from the preprocessing order above.",
      location: "Section 3.3, p. 5",
    },
    {
      id: "metric-1",
      module: "Metrics and uncertainty",
      question: "Do the headline metrics suit an imbalanced task?",
      status: "flag",
      note: "Accuracy is the headline metric on data with about 4% positives. Precision, recall, or PR-AUC would be more informative.",
      quote: "Our model achieves 97.2% accuracy on the held-out test set.",
      location: "Abstract",
    },
    {
      id: "metric-2",
      module: "Metrics and uncertainty",
      question: "Are results reported with variance across runs or confidence intervals?",
      status: "not_reported",
      note: "Single-run results only; no seeds or intervals reported.",
    },
    {
      id: "gen-1",
      module: "Generalizability and limitations",
      question: "Is external validation or a limitations section included?",
      status: "pass",
      note: "A limitations section is present and mentions the single-hospital source.",
      location: "Section 6",
    },
  ],
  claims: [
    {
      claim: "The model detects sepsis with 97.2% accuracy.",
      verdict: "partial",
      reasoning:
        "The figure is reported, but accuracy is dominated by the negative class, so it says little about detecting sepsis.",
      quote: "Our model achieves 97.2% accuracy on the held-out test set.",
      location: "Abstract",
    },
    {
      claim: "The approach generalizes to hospitals broadly.",
      verdict: "overreaching",
      reasoning: "All data comes from a single hospital and there is no external validation.",
      location: "Discussion, p. 9",
    },
  ],
};
