"use client";

import {
  ConsensusMatrix,
  ExpertConsensusPanel,
  OverviewBriefing,
  ReportLoadingState,
  SectionUnavailableState
} from "@/components/kasifpl";
import { PageShell } from "@/components/PageShell";
import { HistoricalReportBadge, MissingReportState, ReportErrorState } from "@/components/report-selection/ReportStates";
import { useSelectedReport } from "@/components/useSelectedReport";

export default function ExpertConsensusPage() {
  const { report: selectedReport, error, isLoadingIndex, isLoadingReport, isMissingReport, isCurrentReport } = useSelectedReport();
  const loading = isLoadingIndex || isLoadingReport;
  const report = selectedReport?.report;
  return (
    <PageShell
      title="Expert Analysis"
      eyebrow="Expert room"
      description="See the recorded team reveals, agreements, disagreements, and late-news flags."
      action={!loading && selectedReport && !isCurrentReport ? <HistoricalReportBadge /> : undefined}
    >
      {loading ? <ReportLoadingState label="Loading expert analysis…" /> : null}
      {!loading && error ? <ReportErrorState /> : null}
      {!loading && !error && isMissingReport ? <MissingReportState /> : null}
      {!loading && !error && report ? (
        <>
          <OverviewBriefing
            overview={report.overview}
            keyRisk={report.key_risk}
            waitForNews={report.wait_for_news}
          />
          {report.disagreements?.length ? (
            <section className="kasifpl-section" aria-labelledby="disagreements-title">
              <h2 className="kasifpl-section__title" id="disagreements-title">Disagreements</h2>
              <div className="kasifpl-grid kasifpl-grid--cols-2">
                {report.disagreements.map((item) => (
                  <article className="kasifpl-card" key={item.topic}>
                    <h3 className="kasifpl-card__title">{item.topic}</h3>
                    <p className="kasifpl-card__body">{item.summary}</p>
                  </article>
                ))}
              </div>
            </section>
          ) : <SectionUnavailableState title="No recorded disagreements" message="The selected report did not include a disagreement section." />}
          <ExpertConsensusPanel reveals={report.expert_team_reveals} />
          <ConsensusMatrix reveals={report.expert_team_reveals} />
        </>
      ) : null}
    </PageShell>
  );
}
