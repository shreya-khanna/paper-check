import type { Status, Verdict, Judgment, FuzzyMatchResult } from "@/lib/types";

const STATUS_LABEL: Record<Status, string> = {
  pass: "Consistent",
  flag: "Flagged",
  not_reported: "Not reported",
  na: "Not applicable",
};

const VERDICT_LABEL: Record<Verdict, string> = {
  supported: "Supported",
  partial: "Partly supported",
  overreaching: "Overreaching",
};

// Verdicts reuse the status colours: supported = pass, partial = not_reported, overreaching = flag.
const VERDICT_TONE: Record<Verdict, string> = {
  supported: "pass",
  partial: "not_reported",
  overreaching: "flag",
};

export const JUDGMENT_META: Record<
  Judgment,
  { label: string; points: number; tone: "pass" | "warn" | "flag" | "critical" }
> = {
  supported: { label: "Supported", points: 100, tone: "pass" },
  insufficient: { label: "Insufficient", points: 50, tone: "warn" },
  concern: { label: "Concern", points: 20, tone: "flag" },
  inconsistency: { label: "Inconsistency", points: 0, tone: "critical" },
};

export function StatusMark({ status }: { status: Status }) {
  return (
    <span className={`mark mark-${status}`}>
      <span className="mark-dot" aria-hidden="true" />
      {STATUS_LABEL[status]}
    </span>
  );
}

export function VerdictMark({ verdict }: { verdict: Verdict }) {
  return (
    <span className={`mark mark-${VERDICT_TONE[verdict]}`}>
      <span className="mark-dot" aria-hidden="true" />
      {VERDICT_LABEL[verdict]}
    </span>
  );
}

export function JudgmentMark({
  judgment,
  showPoints = true,
}: {
  judgment: Judgment;
  showPoints?: boolean;
}) {
  const meta = JUDGMENT_META[judgment] || JUDGMENT_META.insufficient;
  return (
    <span className={`judgment-badge judgment-tone-${meta.tone}`}>
      <span className="judgment-dot" aria-hidden="true" />
      <span className="judgment-label">{meta.label}</span>
      {showPoints && <span className="judgment-pts">{meta.points} pts</span>}
    </span>
  );
}

export function FuzzyMatchBadge({
  fuzzyMatch,
  verified,
  verificationNote,
}: {
  fuzzyMatch?: FuzzyMatchResult;
  verified?: boolean;
  verificationNote?: string;
}) {
  if (!fuzzyMatch && verified === undefined) return null;

  const isVerified = fuzzyMatch?.matched ?? verified ?? false;
  const method = fuzzyMatch?.method;
  const scorePct = fuzzyMatch?.score !== undefined ? Math.round(fuzzyMatch.score * 100) : null;

  if (method === "no_evidence_needed" || verificationNote?.includes("no_evidence_needed")) {
    return (
      <span className="fuzzy-badge fuzzy-badge-neutral" title="Legitimate omission — no quote required">
        <span className="fuzzy-icon">○</span>
        <span>Verified (No Quote Required)</span>
      </span>
    );
  }

  if (!isVerified) {
    return (
      <span
        className="fuzzy-badge fuzzy-badge-failed"
        title={verificationNote || "Quote not verified in source paper text. Downgraded to Insufficient."}
      >
        <span className="fuzzy-icon">⚠</span>
        <span>Verification Failed (Downgraded)</span>
        {scorePct !== null && <span className="fuzzy-score">Match: {scorePct}%</span>}
      </span>
    );
  }

  if (method === "exact") {
    return (
      <span
        className="fuzzy-badge fuzzy-badge-exact"
        title={verificationNote || "Exact verbatim quote confirmed in Docling paper markdown"}
      >
        <span className="fuzzy-icon">✓</span>
        <span>Exact Match Verified</span>
        <span className="fuzzy-score">100%</span>
      </span>
    );
  }

  return (
    <span
      className="fuzzy-badge fuzzy-badge-fuzzy"
      title={
        verificationNote ||
        `Fuzzy sequence matcher confirmed quote in source text with ${scorePct ?? 85}% similarity`
      }
    >
      <span className="fuzzy-icon">⚡</span>
      <span>Fuzzy Match Verified</span>
      {scorePct !== null && <span className="fuzzy-score">{scorePct}%</span>}
    </span>
  );
}

