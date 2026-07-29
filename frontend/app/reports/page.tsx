"use client";

import Link from "next/link";
import { ArchiveGrid, ReportLoadingState } from "@/components/kasifpl";
import { PageShell } from "@/components/PageShell";
import { ReportErrorState } from "@/components/report-selection/ReportStates";
import { useSelectedReport } from "@/components/useSelectedReport";
import { reportHref } from "@/lib/reports/reportHref";

export default function ReportsPage() {
  const { selection, availableSeasons, isLoadingIndex, error } = useSelectedReport();
  const entries = availableSeasons.flatMap((season) =>
    season.gameweeks.map((option) => ({
      season: season.season,
      gameweek: option.gameweek,
      title: option.has_suggested_team ? "Suggested team available" : "Gameweek briefing",
      href: reportHref("/dashboard", { season: season.season, gameweek: option.gameweek }),
      isCurrent: selection?.season === season.season && selection.gameweek === option.gameweek
    }))
  );

  return (
    <PageShell
      title="Historical Reports"
      eyebrow="Archive"
      description="Browse the completed, publicly selectable report snapshots exposed by the backend."
    >
      {isLoadingIndex ? <ReportLoadingState label="Loading the report archive…" /> : null}
      {!isLoadingIndex && error ? <ReportErrorState /> : null}
      {!isLoadingIndex && !error ? (
        <ArchiveGrid
          entries={entries}
          subtitle="Archive cards use only the season, gameweek, update availability, and suggested-team flag supplied by the public index."
          renderLink={({ href, children, ...props }) => <Link href={href} {...props}>{children}</Link>}
        />
      ) : null}
    </PageShell>
  );
}
