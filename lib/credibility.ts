import type { CredibilityAssessment, CredibilityBreakdownItem, CredibilityTier, Report } from "./types";

export function calculateCredibility(report: Report): CredibilityAssessment {
  if (report.credibility) {
    return report.credibility;
  }

  const breakdown: CredibilityBreakdownItem[] = [];

  // 1. Retraction status
  if (report.retraction.status === "retracted") {
    breakdown.push({
      label: "Retraction Notice",
      category: "retraction",
      delta: -60,
      reason: report.retraction.detail ?? "The paper has been retracted by the publisher or authors.",
    });
  } else if (report.retraction.status === "concern") {
    breakdown.push({
      label: "Editorial Concern",
      category: "retraction",
      delta: -25,
      reason: report.retraction.detail ?? "An expression of concern has been issued for this work.",
    });
  }

  // 2. Checklist findings
  const flagged = report.findings.filter((f) => f.status === "flag");
  const notReported = report.findings.filter((f) => f.status === "not_reported");
  const passed = report.findings.filter((f) => f.status === "pass");

  if (flagged.length > 0) {
    const penalty = flagged.length * -12;
    breakdown.push({
      label: "Methodological Flags",
      category: "findings",
      delta: penalty,
      reason: `${flagged.length} critical methodological issue${flagged.length > 1 ? "s" : ""} flagged (e.g. data leakage, improper metrics, or split leakage).`,
    });
  }

  if (notReported.length > 0) {
    const penalty = notReported.length * -4;
    breakdown.push({
      label: "Transparency & Reporting Gaps",
      category: "findings",
      delta: penalty,
      reason: `${notReported.length} checklist item${notReported.length > 1 ? "s" : ""} not reported (e.g. missing code/data statements or run variance).`,
    });
  }

  if (passed.length > 0 && flagged.length === 0 && notReported.length === 0) {
    breakdown.push({
      label: "Consistent Checklist",
      category: "findings",
      delta: 0,
      reason: `All ${passed.length} evaluated checklist items align with standard methodological practices.`,
    });
  }

  // 3. Claims analysis
  const overreaching = report.claims.filter((c) => c.verdict === "overreaching");
  const partial = report.claims.filter((c) => c.verdict === "partial");

  if (overreaching.length > 0) {
    const penalty = overreaching.length * -10;
    breakdown.push({
      label: "Overreaching Claims",
      category: "claims",
      delta: penalty,
      reason: `${overreaching.length} claim${overreaching.length > 1 ? "s" : ""} exceed what the study design and experimental data can support.`,
    });
  }

  if (partial.length > 0) {
    const penalty = partial.length * -4;
    breakdown.push({
      label: "Partially Supported Claims",
      category: "claims",
      delta: penalty,
      reason: `${partial.length} claim${partial.length > 1 ? "s" : ""} are only partially justified by the metrics or evidence.`,
    });
  }

  // Calculate raw score from baseline 100
  const totalDeductions = breakdown.reduce((sum, item) => sum + item.delta, 0);
  const rawScore = 100 + totalDeductions;
  const score = Math.max(0, Math.min(100, rawScore));

  let tier: CredibilityTier;
  let tierLabel: string;
  let summary: string;

  if (score >= 85) {
    tier = "high";
    tierLabel = "High Credibility";
    summary =
      "Methods and reporting appear robust, with claims well-supported by the study design. Suitable for citation under normal academic appraisal.";
  } else if (score >= 65) {
    tier = "moderate";
    tierLabel = "Moderate Credibility";
    summary =
      "Methods are generally sound, but minor reporting omissions or partially supported claims were identified. Check flagged notes before relying on secondary claims.";
  } else if (score >= 40) {
    tier = "low";
    tierLabel = "Low Credibility";
    summary =
      "Significant methodological risks or unsupported claims were detected. Exercise caution and verify code, data splits, and metric suitability prior to citation.";
  } else {
    tier = "critical";
    tierLabel = "Critical Methodological Risk";
    summary =
      "Substantial methodological violations, unverified conclusions, or retraction notices compromise the paper's scientific reliability.";
  }

  return {
    score,
    tier,
    tierLabel,
    summary,
    breakdown,
  };
}
