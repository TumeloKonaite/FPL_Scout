"use client";

import { usePathname } from "next/navigation";
import { GameweekSelector } from "@/components/report-selection/GameweekSelector";

const pageNames: Record<string, string> = {
  "/": "Dashboard", "/dashboard": "Dashboard", "/reports": "Reports",
  "/suggested-team": "Suggested Team", "/captaincy": "Captaincy",
  "/transfers": "Transfers", "/expert-consensus": "Expert Consensus",
  "/admin": "Administration", "/admin/login": "Admin sign in"
};

export function Header() {
  const pathname = usePathname();
  const isReportPage = ["/", "/dashboard", "/reports", "/suggested-team", "/captaincy", "/transfers", "/expert-consensus"].includes(pathname);

  return (
    <header className="header">
      <div className="header-title">
        <span>FPL Technocrat <b>/</b> {pageNames[pathname] ?? "FPL Scout"}</span>
      </div>
      {isReportPage ? <GameweekSelector /> : null}
    </header>
  );
}
