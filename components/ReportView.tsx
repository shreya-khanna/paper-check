import type { Finding, Report } from "@/lib/types";
import { StatusMark, VerdictMark } from "./StatusMark";
import { calculateCredibility } from "@/lib/credibility";
import { CredibilityScore } from "./CredibilityScore";

function groupByModule(findings: Finding[]) {
  const groups = new Map<string, Finding[]>();
  for (const f of findings) {
    groups.set(f.module, [...(groups.get(f.module) ?? []), f]);
  }
  return Array.from(groups.entries());
}

function Evidence({ quote, location }: { quote?: string; location?: string }) {
  if (!quote && !location) return null;
  return (
    <details className="evidence">
      <summary>Show evidence{location ? ` (${location})` : ""}</summary>
      {quote ? <blockquote>{quote}</blockquote> : <p className="muted">No quote available.</p>}
    </details>
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

      {flagged.length > 0 && (
        <section>
          <h2>Worth checking first</h2>
          <div className="rows">
            {flagged.map((f) => (
              <div className="row" key={f.id}>
                <div>
                  <StatusMark status={f.status} />
                </div>
                <div>
                  <p className="question">{f.question}</p>
                  {f.note && <p>{f.note}</p>}
                  <Evidence quote={f.quote} location={f.location} />
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {claims.length > 0 && (
        <section>
          <h2>Claims compared with the experiments</h2>
          <div className="rows">
            {claims.map((c, i) => (
              <div className="row" key={i}>
                <div>
                  <VerdictMark verdict={c.verdict} />
                </div>
                <div>
                  <p className="question">{c.claim}</p>
                  <p>{c.reasoning}</p>
                  <Evidence quote={c.quote} location={c.location} />
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      <section>
        <h2>Full checklist</h2>
        {groupByModule(findings).map(([module, items]) => (
          <div className="module" key={module}>
            <h3>{module}</h3>
            <div className="rows">
              {items.map((f) => (
                <div className="row" key={f.id}>
                  <div>
                    <StatusMark status={f.status} />
                  </div>
                  <div>
                    <p className="question">{f.question}</p>
                    {f.note && <p>{f.note}</p>}
                    <Evidence quote={f.quote} location={f.location} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </section>

      {/* Credibility Score & Ranking Section at the end of the report */}
      <CredibilityScore assessment={assessment} />

      <p className="muted disclaimer">
        This tool points to where a paper needs a closer look. It does not decide whether a paper
        is right. A finding marked not reported means the paper does not mention it, which is
        different from the authors saying they did not do it.
      </p>
    </article>
  );
}

