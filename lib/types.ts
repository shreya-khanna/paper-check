// The contract between your backend and this frontend.
// Have the backend return a `Report` and the UI renders it as-is.

export type Status = "pass" | "flag" | "not_reported" | "na";

export type Finding = {
  id: string;
  module: string; // e.g. a REFORMS module name
  question: string; // the checklist question, in plain language
  status: Status;
  note?: string; // why it was flagged / what was found
  quote?: string; // verbatim evidence from the paper
  location?: string; // e.g. "Section 3.2, p. 5"
};

export type Verdict = "supported" | "partial" | "overreaching";

export type Claim = {
  claim: string;
  verdict: Verdict;
  reasoning: string;
  quote?: string;
  location?: string;
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

