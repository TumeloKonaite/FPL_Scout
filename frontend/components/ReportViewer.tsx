"use client";

import type { FullReportResponse, Report } from "@/src/types/report";
import { RecommendationEvidence } from "@/components/RecommendationEvidence";

type ReportViewerProps = {
  report: FullReportResponse;
};

function EmptySection({ message }: { message: string }) {
  return <p className="empty-copy">{message}</p>;
}

function RecommendationList({
  emptyMessage,
  items
}: {
  emptyMessage: string;
  items?: Report["transfers"];
}) {
  if (!items?.length) {
    return <EmptySection message={emptyMessage} />;
  }

  return (
    <div className="stack-list">
      {items.map((item, index) => (
        <article className="report-item" key={`${item.title}-${index}`}>
          <div className="item-heading">
            <h3>{item.title}</h3>
          </div>
          <p>{item.rationale}</p>
          <RecommendationEvidence recommendation={item} />
        </article>
      ))}
    </div>
  );
}

function TextList({ emptyMessage, items }: { emptyMessage: string; items?: string[] }) {
  if (!items?.length) {
    return <EmptySection message={emptyMessage} />;
  }

  return (
    <ul className="text-list">
      {items.map((item, index) => (
        <li key={`${item}-${index}`}>{item}</li>
      ))}
    </ul>
  );
}

function renderReportSections(report: Report) {
  return (
    <div className="report-sections">
      <section className="report-section">
        <h2>Overview</h2>
        <p>{report.overview}</p>
      </section>

      <section className="report-section" id="transfers">
        <h2>Transfers</h2>
        <RecommendationList
          emptyMessage="No transfer recommendations were generated for this report."
          items={report.transfers}
        />
      </section>

      <section className="report-section" id="captaincy">
        <h2>Captaincy</h2>
        <RecommendationList
          emptyMessage="No captaincy recommendations were generated for this report."
          items={report.captaincy}
        />
      </section>

      <section className="report-section">
        <h2>Chip Strategy</h2>
        <RecommendationList
          emptyMessage="No chip strategy guidance was generated for this report."
          items={report.chip_strategy}
        />
      </section>

      <section className="report-section">
        <h2>Fixture Notes</h2>
        <TextList
          emptyMessage="No fixture-specific notes were captured."
          items={report.fixture_notes}
        />
      </section>

      <section className="report-section">
        <h2>Disagreements</h2>
        {report.disagreements?.length ? (
          <div className="stack-list">
            {report.disagreements.map((item, index) => (
              <article className="report-item" key={`${item.topic}-${index}`}>
                <h3>{item.topic}</h3>
                <p>{item.summary}</p>
                {item.sides?.length ? <p className="muted-copy">{item.sides.join(" | ")}</p> : null}
              </article>
            ))}
          </div>
        ) : (
          <EmptySection message="No major disagreements were highlighted." />
        )}
      </section>

      <section className="report-section" id="risks">
        <h2>Conditional Advice</h2>
        <TextList
          emptyMessage="No conditional advice was generated for this report."
          items={report.conditional_advice}
        />
      </section>

      <section className="report-section">
        <h2>Wait For News</h2>
        <TextList
          emptyMessage="No wait-for-news flags were recorded."
          items={report.wait_for_news}
        />
      </section>

      <section className="report-section">
        <h2>Expert Team Reveals</h2>
        {report.expert_team_reveals?.length ? (
          <div className="stack-list">
            {report.expert_team_reveals.map((item, index) => (
              <article className="report-item" key={`${item.expert_name}-${index}`}>
                <div className="item-heading">
                  <h3>{item.expert_name}</h3>
                </div>
                <p>{item.summary}</p>
                <dl className="detail-grid">
                  <div>
                    <dt>Captain</dt>
                    <dd>{item.captain || "Not specified"}</dd>
                  </div>
                  <div>
                    <dt>Vice-Captain</dt>
                    <dd>{item.vice_captain || "Not specified"}</dd>
                  </div>
                  <div>
                    <dt>Transfers In</dt>
                    <dd>{item.transfers_in?.join(", ") || "None"}</dd>
                  </div>
                  <div>
                    <dt>Transfers Out</dt>
                    <dd>{item.transfers_out?.join(", ") || "None"}</dd>
                  </div>
                </dl>
              </article>
            ))}
          </div>
        ) : (
          <EmptySection message="No expert team reveal data was available for this report." />
        )}
      </section>

      <section className="report-section">
        <h2>Conclusion</h2>
        <p>{report.conclusion}</p>
      </section>
    </div>
  );
}

export function ReportViewer({ report }: ReportViewerProps) {
  return (
    <div className="report-layout">
      <article className="report-panel">
        <header className="report-title">
          <span>{report.report.gameweek ? `GW${report.report.gameweek}` : "Gameweek report"}</span>
          <h2>{report.report.gameweek ? `Gameweek ${report.report.gameweek} recommendations` : "Latest recommendations"}</h2>
        </header>
        {renderReportSections(report.report)}
      </article>
    </div>
  );
}

export function LoadingState({ label }: { label: string }) {
  return <div className="state-panel loading-state">{label}</div>;
}

export function EmptyState({ label }: { label: string }) {
  return <div className="state-panel">{label}</div>;
}

export function ErrorState({ label }: { label: string }) {
  return (
    <div className="state-panel error-state" role="alert">
      {label}
    </div>
  );
}
