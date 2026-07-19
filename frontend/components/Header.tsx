"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { API_BASE_URL } from "@/src/lib/api";

const pageNames: Record<string, string> = {
  "/": "Dashboard", "/dashboard": "Dashboard", "/reports": "Reports",
  "/suggested-team": "Suggested Team", "/captaincy": "Captaincy",
  "/transfers": "Transfers", "/expert-consensus": "Expert Consensus",
  "/pipeline-runner": "Pipeline Runner"
};

export function Header() {
  const pathname = usePathname();
  const [online, setOnline] = useState<boolean | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API_BASE_URL}/health`, { signal: controller.signal })
      .then((response) => setOnline(response.ok))
      .catch(() => setOnline(false));
    return () => controller.abort();
  }, []);

  return (
    <header className="header">
      <div className="header-title">
        <span>Workspace <b>/</b> {pageNames[pathname] ?? "FPL Scout"}</span>
      </div>
      <div className={`header-status ${online ? "online" : online === false ? "offline" : ""}`} aria-label="Backend connection status">
        <i /> {online === null ? "Checking API" : online ? "API connected" : "API offline"}
      </div>
    </header>
  );
}
