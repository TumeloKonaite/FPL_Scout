"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { KasiFplHeader, KasiFplReportSelector, type NavItem, type NavPage } from "@/components/kasifpl";
import { reportHref } from "@/lib/reports/reportHref";
import { useSelectedReport } from "@/components/useSelectedReport";

const pageKeys: Record<string, NavPage> = {
  "/": "briefing",
  "/dashboard": "briefing",
  "/suggested-team": "team",
  "/transfers": "transfers",
  "/captaincy": "captain",
  "/expert-consensus": "experts",
  "/reports": "archive"
};

export function Header() {
  const pathname = usePathname();
  const isReportPage = ["/", "/dashboard", "/reports", "/suggested-team", "/captaincy", "/transfers", "/expert-consensus"].includes(pathname);
  const {
    selection,
    report,
    availableSeasons,
    availableGameweeks,
    isLoadingIndex,
    isCurrentReport,
    setSeason,
    setGameweek
  } = useSelectedReport();
  const navItems: NavItem[] = [
    { key: "briefing", label: "Overview", href: reportHref("/dashboard", selection) },
    { key: "team", label: "Team", href: reportHref("/suggested-team", selection) },
    { key: "transfers", label: "Transfers", href: reportHref("/transfers", selection) },
    { key: "captain", label: "Captaincy", href: reportHref("/captaincy", selection) },
    { key: "experts", label: "Experts", href: reportHref("/expert-consensus", selection) },
    { key: "archive", label: "Archive", href: reportHref("/reports", selection) }
  ];
  const selector = isReportPage && selection ? (
    <KasiFplReportSelector
      selection={selection}
      availableSeasons={availableSeasons.map((item) => item.season)}
      availableGameweeks={availableGameweeks.map((item) => item.gameweek)}
      onSeasonChange={setSeason}
      onGameweekChange={setGameweek}
      deadline={report?.report.deadline}
      isCurrentReport={isCurrentReport}
      disabled={isLoadingIndex}
    />
  ) : null;

  return (
    <KasiFplHeader
      activePage={pageKeys[pathname]}
      brandHref={reportHref("/", selection)}
      navItems={isReportPage ? navItems : []}
      rightSlot={selector}
      renderLink={({ href, children, ...props }) => <Link href={href} {...props}>{children}</Link>}
    />
  );
}
