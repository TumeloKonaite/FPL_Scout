"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";
import Link from "next/link";
import { PageShell } from "@/components/PageShell";
import { HistoricalReportBadge, MissingReportState, ReportErrorState } from "@/components/report-selection/ReportStates";
import { Icon } from "@/components/Icons";
import { validateStartingXi } from "@/components/suggestedTeam";
import type { KeyRisk } from "@/src/types/report";
import { RecommendationEvidence } from "@/components/RecommendationEvidence";
import { useSelectedReport } from "@/components/useSelectedReport";
import { reportHref } from "@/lib/reports/reportHref";
import { deadlineState } from "@/lib/reports/reportStatus";
import { seasonLabel } from "@/lib/reports/reportSelection";

type ActionItem = { text: string; href: string };

function parseDate(value?: string | null): Date | null {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function formatDateTime(value?: string | null): string | null {
  const date = parseDate(value);
  if (!date) return null;
  return new Intl.DateTimeFormat(undefined, {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZoneName: "short"
  }).format(date);
}

function DeadlineCountdown({ deadline, historical }: { deadline?: string | null; historical: boolean }) {
  const [now, setNow] = useState(() => Date.now());
  const target = parseDate(deadline)?.getTime();

  useEffect(() => {
    if (!target || target <= Date.now()) return;
    const timer = window.setInterval(() => setNow(Date.now()), 60_000);
    return () => window.clearInterval(timer);
  }, [target]);

  const state = deadlineState(deadline, historical, now);
  if (state === "missing") return <span className="deadline-status">Deadline unavailable</span>;
  if (state === "passed") return <span className="deadline-status">Deadline passed</span>;
  if (!target) return <span className="deadline-status">Deadline unavailable</span>;
  const totalMinutes = Math.ceil((target - now) / 60_000);
  const days = Math.floor(totalMinutes / 1_440);
  const hours = Math.floor((totalMinutes % 1_440) / 60);
  const minutes = totalMinutes % 60;
  const parts = [days ? `${days} day${days === 1 ? "" : "s"}` : "", hours ? `${hours} hour${hours === 1 ? "" : "s"}` : "", !days && minutes ? `${minutes} min` : ""].filter(Boolean);
  return <span className="deadline-countdown">Deadline in {parts.slice(0, 2).join(", ")}</span>;
}

function DashboardSkeleton() {
  return (
    <div className="dashboard-skeleton" aria-label="Loading the latest gameweek summary" aria-live="polite">
      <span className="visually-hidden">Loading the latest gameweek summary...</span>
      <div className="skeleton-block skeleton-meta" />
      <div className="summary-card-grid">
        <div className="skeleton-block skeleton-card" />
        <div className="skeleton-block skeleton-card" />
        <div className="skeleton-block skeleton-card" />
      </div>
      <div className="skeleton-block skeleton-wide" />
    </div>
  );
}

function SummaryLink({ href, children }: { href: string; children: ReactNode }) {
  return <Link className="summary-link" href={href}>{children}<Icon name="arrow" /></Link>;
}

export default function DashboardPage() {
  const { selection, report: selectedReport, error, isLoadingIndex, isLoadingReport, isMissingReport, isCurrentReport } = useSelectedReport();
  const isLoading = isLoadingIndex || isLoadingReport;
  const report = selectedReport?.report;
  const lastUpdated = report?.lastUpdated ?? selectedReport?.last_updated_at ?? null;
  const topCaptain = report?.captaincy?.[0];
  const topTransfer = report?.transfers?.[0];
  const keyRisk = useMemo<KeyRisk | null>(() => report?.key_risk ?? (report?.wait_for_news?.[0] ? {
    subject: "News to monitor",
    riskType: "Availability risk",
    explanation: report.wait_for_news[0]
  } : null), [report?.key_risk, report?.wait_for_news]);

  const lineup = useMemo(() => {
    const team = report?.suggested_team;
    if (!team) return null;
    const result = validateStartingXi(team.startingXi, team.formation);
    return result.valid ? result : null;
  }, [report?.suggested_team]);

  const actions = useMemo(() => {
    const items: ActionItem[] = [];
    if (topCaptain) items.push({ text: `Captain ${topCaptain.playerName || topCaptain.title}.`, href: reportHref("/captaincy", selection) });
    if (topTransfer) items.push({ text: topTransfer.playerIn ? `Consider transferring ${topTransfer.playerIn} in.` : `Prioritise: ${topTransfer.title}.`, href: reportHref("/transfers", selection) });
    if (keyRisk) items.push({ text: keyRisk.recommendedAction || `Monitor ${keyRisk.subject.toLowerCase()} before the deadline.`, href: reportHref("/reports#risks", selection) });
    for (const advice of report?.conditional_advice ?? []) {
      if (items.length >= 5) break;
      if (advice.trim()) items.push({ text: advice, href: reportHref("/reports#risks", selection) });
    }
    for (const strategy of report?.chip_strategy ?? []) {
      if (items.length >= 5) break;
      if (strategy.title.trim()) items.push({ text: strategy.title, href: reportHref("/reports", selection) });
    }
    return items;
  }, [keyRisk, report?.chip_strategy, report?.conditional_advice, selection, topCaptain, topTransfer]);

  const gameweekLabel = report?.gameweek ? ` — GW${report.gameweek}` : "";
  const formattedDeadline = formatDateTime(report?.deadline);
  const formattedUpdated = formatDateTime(lastUpdated);

  return (
    <PageShell
      title={isCurrentReport ? `This Gameweek${gameweekLabel}` : selection ? `Gameweek ${selection.gameweek} — ${seasonLabel(selection.season)}` : "Gameweek report"}
      eyebrow="Your weekly briefing"
      description={isCurrentReport ? "The latest expert consensus, distilled into the decisions that matter before the deadline." : "A read-only snapshot of the recommendations published for this historical gameweek."}
      action={!isLoading && selectedReport && !isCurrentReport ? <HistoricalReportBadge /> : undefined}
    >
      {isLoading ? <DashboardSkeleton /> : null}
      {!isLoading && error ? <ReportErrorState /> : null}
      {!isLoading && !error && isMissingReport ? <MissingReportState /> : null}

      {!isLoading && !error && report ? (
        <div className="gameweek-dashboard">
          <section className="gameweek-metadata" aria-label="Gameweek timing">
            <div>
              <span className="metadata-label">{report.gameweek ? `Gameweek ${report.gameweek} deadline` : "Gameweek deadline"}</span>
              <strong>{formattedDeadline ? `Deadline: ${formattedDeadline}` : "Deadline unavailable"}</strong>
              <DeadlineCountdown deadline={report.deadline} historical={!isCurrentReport} />
            </div>
            <div>
              <span className="metadata-label">Recommendations</span>
              <strong>{formattedUpdated ? `Last updated: ${formattedUpdated}` : "Last updated time unavailable"}</strong>
            </div>
          </section>

          <section className="summary-card-grid" aria-label="Top gameweek recommendations">
            <article className="summary-card captain-card">
              <span className="summary-card-icon" aria-hidden="true"><Icon name="captain" /></span>
              <span className="eyebrow">Top Captain</span>
              {topCaptain ? <>
                <h2>{topCaptain.playerName || topCaptain.title}</h2>
                {topCaptain.club || topCaptain.opponent ? <p className="player-fixture">{[topCaptain.club, topCaptain.opponent ? `${topCaptain.opponent}${topCaptain.venue ? ` (${topCaptain.venue === "home" ? "H" : "A"})` : ""}` : null].filter(Boolean).join(" vs ")}</p> : null}
                <RecommendationEvidence recommendation={topCaptain} compact />
                <p>{topCaptain.rationale}</p>
                {topCaptain.viceCaptain ? <p className="secondary-detail">Vice-captain: {topCaptain.viceCaptain}</p> : null}
              </> : <p>No clear captain consensus was identified for this gameweek.</p>}
              <SummaryLink href={reportHref("/captaincy", selection)}>View captaincy analysis</SummaryLink>
            </article>

            <article className="summary-card transfer-card">
              <span className="summary-card-icon" aria-hidden="true"><Icon name="transfers" /></span>
              <span className="eyebrow">Top Transfer</span>
              {topTransfer ? <>
                <h2>{topTransfer.playerIn ? `Buy: ${topTransfer.playerIn}` : topTransfer.title}</h2>
                {topTransfer.playerOut ? <p className="player-fixture">Sell: {topTransfer.playerOut}</p> : null}
                {topTransfer.position || topTransfer.price != null ? <p className="secondary-detail">{[topTransfer.position, topTransfer.price != null ? `£${topTransfer.price.toFixed(1)}m` : null].filter(Boolean).join(" · ")}</p> : null}
                <RecommendationEvidence recommendation={topTransfer} compact />
                <p>{topTransfer.rationale}</p>
              </> : <p>No clear transfer consensus was identified for this gameweek.</p>}
              <SummaryLink href={reportHref("/transfers", selection)}>View transfer recommendations</SummaryLink>
            </article>

            <article className="summary-card risk-card">
              <span className="summary-card-icon" aria-hidden="true"><Icon name="alert" /></span>
              <span className="eyebrow">Key Risk</span>
              {keyRisk ? <>
                <h2>{keyRisk.subject}{keyRisk.riskType ? ` — ${keyRisk.riskType}` : ""}</h2>
                <p>{keyRisk.explanation}</p>
                {keyRisk.recommendedAction ? <p className="risk-response"><strong>Recommendation:</strong> {keyRisk.recommendedAction}</p> : null}
              </> : <p>No major risk was identified in the latest analysis.</p>}
              <SummaryLink href={reportHref("/reports#risks", selection)}>View risks</SummaryLink>
            </article>
          </section>

          <section className="dashboard-section action-plan" aria-labelledby="action-plan-title">
            <div className="section-heading"><div><span className="eyebrow">Before the deadline</span><h2 id="action-plan-title">Your Gameweek Action Plan</h2></div><span>{actions.length} priorities</span></div>
            {actions.length ? <ol>{actions.map((action, index) => <li key={`${action.text}-${index}`}><span>{index + 1}</span><Link href={action.href}>{action.text}<Icon name="arrow" /></Link></li>)}</ol> : <p className="empty-copy">No specific actions were identified in the latest report.</p>}
          </section>

          <section className="dashboard-section consensus-preview" aria-labelledby="consensus-title">
            <div className="section-heading"><div><span className="eyebrow">Recommended lineup</span><h2 id="consensus-title">Consensus XI{lineup ? ` — ${lineup.formation}` : ""}</h2></div><SummaryLink href={reportHref("/suggested-team", selection)}>View full suggested team</SummaryLink></div>
            {lineup ? <div className="position-groups">
              {([ ["GK", lineup.groupedPlayers.goalkeeper], ["DEF", lineup.groupedPlayers.defenders], ["MID", lineup.groupedPlayers.midfielders], ["FWD", lineup.groupedPlayers.forwards] ] as const).map(([position, players]) => <div className="position-row" key={position}><strong>{position}</strong><div>{players.map((player) => <span className="preview-player" key={player.playerId}>{player.name}{player.captain ? <abbr title="Captain" aria-label="Captain"> C</abbr> : null}{player.viceCaptain ? <abbr title="Vice-captain" aria-label="Vice-captain"> VC</abbr> : null}</span>)}</div></div>)}
            </div> : <p className="empty-copy">A valid consensus starting XI is not available for this gameweek.</p>}
          </section>
        </div>
      ) : null}
    </PageShell>
  );
}
