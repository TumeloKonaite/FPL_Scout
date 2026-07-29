import * as React from "react";
import type { KeyRisk, Report } from "../types";
import { SectionUnavailableState } from "./SectionUnavailableState";

export type OverviewBriefingProps = {
  overview: string;
  conclusion?: string;
  keyRisk?: KeyRisk | null;
  fixtureNotes?: string[];
  waitForNews?: string[];
  conditionalAdvice?: string[];
};

export function OverviewBriefing(props: OverviewBriefingProps) {
  const { overview, conclusion, keyRisk, fixtureNotes, waitForNews, conditionalAdvice } = props;
  return (
    <div className="kasifpl-card">
      <div className="kasifpl-card__header">
        <div>
          <h2 className="kasifpl-card__title">This week&apos;s briefing</h2>
          <p className="kasifpl-card__subtitle">Summary of the current gameweek report</p>
        </div>
      </div>
      <div className="kasifpl-card__body">
        {overview ? <p className="kasifpl-briefing__overview">{overview}</p> : null}
        {keyRisk ? (
          <div className="kasifpl-card" style={{ marginTop: 16, borderColor: "rgba(239,68,68,0.35)" }}>
            <div className="kasifpl-card__header">
              <div>
                <h3 className="kasifpl-card__title">Key risk: {keyRisk.subject}</h3>
                {keyRisk.riskType ? <p className="kasifpl-card__subtitle">{keyRisk.riskType}</p> : null}
              </div>
              <span className="kasifpl-chip kasifpl-chip--danger">Risk</span>
            </div>
            <div className="kasifpl-card__body">
              <p>{keyRisk.explanation}</p>
              {keyRisk.recommendedAction ? (
                <p style={{ marginTop: 8 }}><strong>Action:</strong> {keyRisk.recommendedAction}</p>
              ) : null}
            </div>
          </div>
        ) : null}
        {waitForNews && waitForNews.length ? (
          <div style={{ marginTop: 16 }}>
            <h3 className="kasifpl-card__title" style={{ fontSize: "0.9375rem" }}>Wait for news</h3>
            <ul style={{ margin: "6px 0 0 20px", padding: 0 }}>
              {waitForNews.map((w, i) => <li key={i}>{w}</li>)}
            </ul>
          </div>
        ) : null}
        {conditionalAdvice && conditionalAdvice.length ? (
          <div style={{ marginTop: 16 }}>
            <h3 className="kasifpl-card__title" style={{ fontSize: "0.9375rem" }}>Conditional advice</h3>
            <ul style={{ margin: "6px 0 0 20px", padding: 0 }}>
              {conditionalAdvice.map((c, i) => <li key={i}>{c}</li>)}
            </ul>
          </div>
        ) : null}
        {fixtureNotes && fixtureNotes.length ? (
          <div style={{ marginTop: 16 }}>
            <h3 className="kasifpl-card__title" style={{ fontSize: "0.9375rem" }}>Fixture notes</h3>
            <ul style={{ margin: "6px 0 0 20px", padding: 0 }}>
              {fixtureNotes.map((n, i) => <li key={i}>{n}</li>)}
            </ul>
          </div>
        ) : null}
        {conclusion ? (
          <div style={{ marginTop: 16 }}>
            <h3 className="kasifpl-card__title" style={{ fontSize: "0.9375rem" }}>Conclusion</h3>
            <p style={{ marginTop: 6 }}>{conclusion}</p>
          </div>
        ) : null}
        {!overview && !conclusion ? (
          <SectionUnavailableState message="No briefing text supplied for this report." />
        ) : null}
      </div>
    </div>
  );
}

/** Convenience projection from Report. */
export function OverviewBriefingFromReport({ report }: { report: Report }) {
  return (
    <OverviewBriefing
      overview={report.overview}
      conclusion={report.conclusion}
      keyRisk={report.key_risk ?? null}
      fixtureNotes={report.fixture_notes}
      waitForNews={report.wait_for_news}
      conditionalAdvice={report.conditional_advice}
    />
  );
}
