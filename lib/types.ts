// The contract between your backend and this frontend.
// Have the backend return a `Report` and the UI renders it as-is.

export type Status = "pass" | "flag" | "not_reported" | "na";

export type Judgment = "supported" | "concern" | "insufficient" | "inconsistency";

export type FuzzyMatchMethod = "exact" | "fuzzy" | "none" | "no_evidence_needed";

export type FuzzyMatchResult = {
  matched: boolean;
  score?: number; // 0.0 to 1.0 similarity ratio (e.g. 0.96 = 96%)
  method: FuzzyMatchMethod;
  note?: string;
  matchedSnippet?: string;
};

export type Finding = {
  id: string;
  module: string; // e.g. a REFORMS module name
  question: string; // the checklist question, in plain language
  status: Status;
  judgment?: Judgment;
  note?: string; // why it was flagged / what was found
  quote?: string; // verbatim evidence from the paper
  location?: string; // e.g. "Section 3.2, p. 5"
  verified?: boolean;
  verificationNote?: string;
  fuzzyMatch?: FuzzyMatchResult;
};

export type Verdict = "supported" | "partial" | "overreaching";

export type Claim = {
  claim: string;
  verdict: Verdict;
  judgment?: Judgment;
  reasoning: string;
  quote?: string;
  location?: string;
  verified?: boolean;
  verificationNote?: string;
  fuzzyMatch?: FuzzyMatchResult;
};

export type CredibilityTier = "high" | "moderate" | "low" | "critical";

export type CredibilityBreakdownItem = {
  label: string;
  category: "retraction" | "findings" | "claims" | "general";
  delta: number;
  reason: string;
};

export type CredibilityAssessment = {
  score: number; // 0 to 100
  tier: CredibilityTier;
  tierLabel: string;
  summary: string;
  breakdown: CredibilityBreakdownItem[];
};

export type Report = {
  paper: {
    title: string;
    authors: string[];
    venue?: string;
    year?: number;
    doi?: string;
    isPreprint: boolean;
  };
  retraction: {
    status: "none" | "retracted" | "concern";
    detail?: string;
  };
  paperType: string; // e.g. "Machine learning, classification"
  checklistApplies: "full" | "partial";
  findings: Finding[];
  claims: Claim[];
  credibility?: CredibilityAssessment;
};


