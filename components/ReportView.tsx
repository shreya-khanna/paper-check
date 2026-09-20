import type { Finding, Report, FuzzyMatchResult } from "@/lib/types";
import { StatusMark, VerdictMark, JudgmentMark, FuzzyMatchBadge } from "./StatusMark";
import { calculateCredibility } from "@/lib/credibility";
import { CredibilityScore } from "./CredibilityScore";

function groupByModule(findings: Finding[]) {
  const groups = new Map<string, Finding[]>();
  for (const f of findings) {
    groups.set(f.module, [...(groups.get(f.module) ?? []), f]);
  }
  return Array.from(groups.entries());
}

function Evidence({
  quote,
  location,
  verified,
  verificationNote,
  fuzzyMatch,
}: {
  quote?: string;
  location?: string;
  verified?: boolean;
  verificationNote?: string;
  fuzzyMatch?: FuzzyMatchResult;
}) {
  if (!quote && !location && !fuzzyMatch && verified === undefined) return null;
  return (
    <div className="evidence-wrapper">
      <div className="evidence-badges">
        <FuzzyMatchBadge
          fuzzyMatch={fuzzyMatch}
          verified={verified}
          verificationNote={verificationNote}
        />
        {location && <span className="location-tag">{location}</span>}
      </div>
      {(quote || verificationNote) && (
        <details className="evidence">
          <summary>
            Show verified quote evidence{location ? ` (${location})` : ""}
          </summary>
          {quote ? (
            <blockquote>
              {quote}
              {fuzzyMatch?.note && (
                <div className="quote-fuzzy-info">
                  <span className="fuzzy-info-label">verify.py:</span> {fuzzyMatch.note}
                </div>
              )}
            </blockquote>
          ) : (
            <p className="muted">No direct quote available.</p>
          )}
        </details>
      )}
    </div>
  );
}

const RETRACTION_TEXT = {
  none: "No retraction or correction notice found",
  retracted: "Retracted",
  concern: "Expression of concern issued",
} as const;

export function ReportView({ report }: { report: Report }) {
  const { paper, retraction, findings, claims } = report;
  const flagged = findings.filter((f) => f.status === "flag");
  const count = (s: Finding["status"]) => findings.filter((f) => f.status === s).length;
  const assessment = calculateCredibility(report);

  return (
    <article className="report">
      {retraction.status !== "none" && (
        <div className="notice" role="alert">
          <strong>{RETRACTION_TEXT[retraction.status]}.</strong>{" "}
          {retraction.detail ?? "Check the publisher page before citing this paper."}
        </div>
      )}

      {/* Pipeline Stepper Banner */}
      <div className="pipeline-banner">
        <div className="pipeline-header">
          <span className="pipeline-title">Audit & Verification Pipeline</span>
          <span className="pipeline-tag">Docling OCR + Gemini LLM + verify.py Fuzzy Matching</span>
        </div>
        <div className="pipeline-steps">
          <div className="pipeline-step completed">
            <div className="step-num">1</div>
            <div className="step-content">
              <strong>Docling OCR</strong>
              <span>PDF to Structured Markdown</span>
            </div>
          </div>
          <div className="pipeline-step completed">
            <div className="step-num">2</div>
            <div className="step-content">
              <strong>Content Extraction</strong>
              <span>Structured schema dictionary</span>
            </div>
          </div>
          <div className="pipeline-step completed">
            <div className="step-num">3</div>
            <div className="step-content">
              <strong>Guideline Audit</strong>
              <span>Criterion judgment scoring</span>
            </div>
          </div>
          <div className="pipeline-step completed active-glow">
            <div className="step-num">4</div>
            <div className="step-content">
              <strong>Evidence Verification</strong>
              <span>Fuzzy Sequence Matching (≥85%)</span>
            </div>
          </div>
        </div>
      </div>

      <section className="summary">
        <h2 className="paper-title">{paper.title}</h2>
        <p className="muted">
          {[paper.authors.join(", "), paper.venue, paper.year].filter(Boolean).join(", ")}
        </p>
        <dl className="facts">
          <div>
            <dt>Retraction status</dt>
            <dd>{RETRACTION_TEXT[retraction.status]}</dd>
          </div>
          <div>
            <dt>Publication</dt>
            <dd>{paper.isPreprint ? "Preprint, not peer reviewed" : "Published"}</dd>
          </div>
          <div>
            <dt>Paper type</dt>
            <dd>{report.paperType}</dd>
          </div>
          <div>
            <dt>Checklist coverage</dt>
            <dd>
              {report.checklistApplies === "full"
                ? "Fully applies"
                : "Partly applies; some items may not fit this field"}
            </dd>
          </div>
          <div>
            <dt>Checklist findings</dt>
            <dd>
              {count("flag")} flagged, {count("not_reported")} not reported, {count("pass")}{" "}
              consistent
            </dd>
          </div>
          <div>
            <dt>Credibility rank</dt>
            <dd>
              <span className={`facts-score-pill score-tone-${assessment.tier}`}>
                <strong>{assessment.score}/100</strong> — {assessment.tierLabel}
              </span>
            </dd>
          </div>
        </dl>
      </section>

      {/* Judgment Scoring Weights Callout */}
      <div className="scoring-formula-card">
        <div className="scoring-formula-title">Audit Criterion Judgment Weights</div>
        <div className="scoring-formula-pills">
          <span className="formula-pill tone-pass">
            <strong>Supported</strong> = 100 pts
          </span>
          <span className="formula-pill tone-warn">
            <strong>Insufficient</strong> = 50 pts
          </span>
          <span className="formula-pill tone-flag">
            <strong>Concern</strong> = 20 pts
          </span>
          <span className="formula-pill tone-critical">
            <strong>Inconsistency</strong> = 0 pts
          </span>
        </div>
        <p className="scoring-formula-note">
          Every finding & claim quote is fuzzy-matched against Docling OCR source text.
          Unverified or hallucinated quotes are automatically downgraded to Insufficient (50 pts).
        </p>
      </div>

      {flagged.length > 0 && (
        <section>
          <h2>Worth checking first</h2>
          <div className="rows">
            {flagged.map((f) => {
              const itemJudgment =
                f.judgment ?? (f.status === "pass" ? "supported" : "concern");
              return (
                <div className="row" key={f.id}>
                  <div className="row-marks">
                    <StatusMark status={f.status} />
                    <JudgmentMark judgment={itemJudgment} />
                  </div>
                  <div>
                    <p className="question">{f.question}</p>
                    {f.note && <p>{f.note}</p>}
                    <Evidence
                      quote={f.quote}
                      location={f.location}
                      verified={f.verified}
                      verificationNote={f.verificationNote}
                      fuzzyMatch={f.fuzzyMatch}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {claims.length > 0 && (
        <section>
          <div className="section-title-row">
            <h2>Claims compared with the experiments</h2>
            <span className="section-subtext">Verified with Docling OCR & Fuzzy Matching</span>
          </div>
          <div className="rows">
            {claims.map((c, i) => {
              const itemJudgment =
                c.judgment ??
                (c.verdict === "supported"
                  ? "supported"
                  : c.verdict === "overreaching"
                  ? "concern"
                  : "insufficient");
              return (
                <div className="row claim-row" key={i}>
                  <div className="row-marks">
                    <VerdictMark verdict={c.verdict} />
                    <JudgmentMark judgment={itemJudgment} />
                  </div>
                  <div>
                    <p className="question">{c.claim}</p>
                    <p>{c.reasoning}</p>
                    <Evidence
                      quote={c.quote}
                      location={c.location}
                      verified={c.verified}
                      verificationNote={c.verificationNote}
                      fuzzyMatch={c.fuzzyMatch}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      <section>
        <h2>Full checklist</h2>
        {groupByModule(findings).map(([module, items]) => (
          <div className="module" key={module}>
            <h3>{module}</h3>
            <div className="rows">
              {items.map((f) => {
                const itemJudgment =
                  f.judgment ??
                  (f.status === "pass"
                    ? "supported"
                    : f.status === "flag"
                    ? "concern"
                    : "insufficient");
                return (
                  <div className="row" key={f.id}>
                    <div className="row-marks">
                      <StatusMark status={f.status} />
                      <JudgmentMark judgment={itemJudgment} />
                    </div>
                    <div>
                      <p className="question">{f.question}</p>
                      {f.note && <p>{f.note}</p>}
                      <Evidence
                        quote={f.quote}
                        location={f.location}
                        verified={f.verified}
                        verificationNote={f.verificationNote}
                        fuzzyMatch={f.fuzzyMatch}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </section>

      {/* Credibility Score & Ranking Section at the end of the report */}
      <CredibilityScore assessment={assessment} />

      <p className="muted disclaimer">
        This tool points to where a paper needs a closer look. It does not decide whether a paper
        is right. A finding marked not reported or insufficient means the paper does not mention it,
        which is different from the authors saying they did not do it.
      </p>
    </article>
  );
}


