import type { CredibilityAssessment } from "@/lib/types";

export function CredibilityScore({ assessment }: { assessment: CredibilityAssessment }) {
  const { score, tier, tierLabel, summary, breakdown } = assessment;

  return (
    <section className="credibility-section">
      <div className="credibility-card">
        <div className="credibility-header">
          <div className="credibility-score-block">
            <span className="credibility-title">Paper Credibility Score</span>
            <div className="credibility-score-display">
              <span className={`score-number score-tone-${tier}`}>{score}</span>
              <span className="score-denominator">/ 100</span>
            </div>
          </div>
          <div className="credibility-badge-block">
            <span className={`tier-badge tier-${tier}`}>
              <span className="tier-dot" aria-hidden="true" />
              {tierLabel}
            </span>
          </div>
        </div>

        {/* Visual Score Meter */}
        <div className="credibility-meter-container" aria-label={`Score: ${score} out of 100`}>
          <div className="credibility-meter-track">
            <div
              className={`credibility-meter-fill fill-${tier}`}
              style={{ width: `${Math.max(4, score)}%` }}
            />
          </div>
          <div className="credibility-meter-labels">
            <span className="meter-label">0 (Critical)</span>
            <span className="meter-label">40 (Low)</span>
            <span className="meter-label">65 (Moderate)</span>
            <span className="meter-label">85 (High)</span>
            <span className="meter-label">100</span>
          </div>
        </div>

        {/* Assessment Summary */}
        <p className="credibility-summary">{summary}</p>

        {/* Point Breakdown */}
        {breakdown.length > 0 && (
          <div className="credibility-breakdown">
            <h4 className="breakdown-heading">Score Breakdown</h4>
            <div className="breakdown-list">
              <div className="breakdown-item baseline">
                <span className="breakdown-label">Baseline Score</span>
                <span className="breakdown-points neutral">100 pts</span>
              </div>
              {breakdown.map((item, idx) => (
                <div className="breakdown-item" key={idx}>
                  <div className="breakdown-info">
                    <span className="breakdown-label">{item.label}</span>
                    <span className="breakdown-reason">{item.reason}</span>
                  </div>
                  <span
                    className={`breakdown-points ${item.delta < 0 ? "negative" : item.delta > 0 ? "positive" : "neutral"}`}
                  >
                    {item.delta > 0 ? `+${item.delta}` : `${item.delta}`} pts
                  </span>
                </div>
              ))}
              <div className="breakdown-item total">
                <span className="breakdown-label">Final Computed Score</span>
                <span className={`breakdown-points score-tone-${tier}`}>{score} / 100</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
