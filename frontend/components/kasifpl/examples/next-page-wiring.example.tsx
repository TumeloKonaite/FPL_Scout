/**
 * Example wiring for a Next.js 15 App Router page.
 *
 * This file is illustrative. It contains NO mock data, NO API calls, and NO
 * router imports. Replace the `useReportSelection` / `useReport` hooks with
 * your host app's real report-selection provider and data source.
 *
 * Copy this file into e.g. `app/(kasifpl)/[season]/[gameweek]/page.tsx` and
 * adapt the imports.
 */

"use client";

import * as React from "react";
import Link from "next/link"; // host app dependency, not the pack's
import {
  ApiErrorState,
  ArchiveGrid,
  CaptaincyPanel,
  ConsensusMatrix,
  ExpertConsensusPanel,
  KasiFplFooter,
  KasiFplHeader,
  KasiFplPageShell,
  KasiFplReportSelector,
  OverviewBriefingFromReport,
  ReportLoadingState,
  ReportUnavailableState,
  SuggestedTeamBench,
  SuggestedTeamPitch,
  TransfersPanel,
  type ArchiveEntry,
  type NavItem,
  type Report,
  type ReportSelection,
} from "../index";

// Provided by the host application. These are placeholders — do not treat them
// as part of the component pack.
declare function useReportSelection(): {
  selection: ReportSelection;
  availableSeasons: string[];
  availableGameweeks: number[];
  setSeason: (s: string) => void;
  setGameweek: (gw: number) => void;
  isCurrentReport: boolean;
};
declare function useReport(selection: ReportSelection): {
  report: Report | null;
  archive: ArchiveEntry[];
  loading: boolean;
  error: Error | null;
  refresh: () => void;
};

export default function KasiFplPage() {
  const {
    selection, availableSeasons, availableGameweeks,
    setSeason, setGameweek, isCurrentReport,
  } = useReportSelection();
  const { report, archive, loading, error, refresh } = useReport(selection);

  const navItems: NavItem[] = [
    { key: "briefing", label: "Briefing", href: `/kasifpl/${selection.season}/${selection.gameweek}` },
    { key: "team",     label: "Team",     href: `/kasifpl/${selection.season}/${selection.gameweek}/team` },
    { key: "transfers",label: "Transfers",href: `/kasifpl/${selection.season}/${selection.gameweek}/transfers` },
    { key: "captain",  label: "Captain",  href: `/kasifpl/${selection.season}/${selection.gameweek}/captain` },
    { key: "experts",  label: "Experts",  href: `/kasifpl/${selection.season}/${selection.gameweek}/experts` },
    { key: "archive",  label: "Archive",  href: `/kasifpl/archive` },
  ];

  return (
    <KasiFplPageShell
      header={
        <KasiFplHeader
          navItems={navItems}
          activePage="briefing"
          renderLink={({ href, children, ...rest }) => (
            <Link href={href} {...rest}>{children}</Link>
          )}
        />
      }
      footer={<KasiFplFooter>KasiFPL · analysis is informational, not financial advice.</KasiFplFooter>}
    >
      <KasiFplReportSelector
        selection={selection}
        availableSeasons={availableSeasons}
        availableGameweeks={availableGameweeks}
        onSeasonChange={setSeason}
        onGameweekChange={setGameweek}
        deadline={report?.deadline ?? null}
        isCurrentReport={isCurrentReport}
      />

      {loading ? <ReportLoadingState /> : null}

      {!loading && error ? (
        <ApiErrorState detail={error.message} onRetry={refresh} />
      ) : null}

      {!loading && !error && !report ? <ReportUnavailableState /> : null}

      {!loading && !error && report ? (
        <>
          <div style={{ height: 16 }} />
          <div className="kasifpl-grid kasifpl-grid--cols-2">
            <OverviewBriefingFromReport report={report} />
            <SuggestedTeamPitch team={report.suggested_team ?? null} />
          </div>
          <SuggestedTeamBench team={report.suggested_team ?? null} />
          <CaptaincyPanel captaincy={report.captaincy} limit={2} />
          <TransfersPanel transfers={report.transfers} compact />
          <ExpertConsensusPanel reveals={report.expert_team_reveals} />
          <ConsensusMatrix reveals={report.expert_team_reveals} />
          <ArchiveGrid
            entries={archive}
            renderLink={({ href, children, ...rest }) => (
              <Link href={href} {...rest}>{children}</Link>
            )}
          />
        </>
      ) : null}
    </KasiFplPageShell>
  );
}
