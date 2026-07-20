"use client";

import { useEffect, useState } from "react";
import { ApiError, getCurrentGameweek, getLatestReport } from "@/src/lib/api";
import type { FullReportResponse } from "@/src/types/report";

export function useLatestReport() {
  const [data, setData] = useState<FullReportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [unavailable, setUnavailable] = useState(false);

  useEffect(() => {
    let active = true;
    Promise.all([getCurrentGameweek(), getLatestReport()])
      .then(([current, report]) => {
        if (!active) return;
        const reportGameweek = report.gameweek ?? report.report.gameweek;
        if (!current.recommendations_available || current.gameweek == null || reportGameweek !== current.gameweek) {
          setUnavailable(true);
          return;
        }
        setData(report);
      })
      .catch((reason: unknown) => {
        if (!active) return;
        if (reason instanceof ApiError && reason.status === 404) setUnavailable(true);
        else setError("The latest gameweek analysis is temporarily unavailable.");
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  return { data, error, loading, unavailable };
}
