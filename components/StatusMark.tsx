import type { Status, Verdict } from "@/lib/types";

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
