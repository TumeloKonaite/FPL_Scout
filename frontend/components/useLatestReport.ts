"use client";

import { useEffect, useState } from "react";
import { getErrorMessage } from "./apiError";
import { getLatestReport } from "@/src/lib/api";
import type { FullReportResponse } from "@/src/types/report";

export function useLatestReport() {
  const [data, setData] = useState<FullReportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    getLatestReport()
      .then((report) => { if (active) setData(report); })
      .catch((caught) => { if (active) setError(getErrorMessage(caught)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  return { data, error, loading };
}
