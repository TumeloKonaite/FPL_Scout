"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { ApiError, getAvailableGameweeks, getCurrentGameweek, getSelectedReport } from "@/src/lib/api";
import type { FullReportResponse, GameweekOption, SeasonOption } from "@/src/types/report";
import { isCurrentSelection } from "@/lib/reports/reportStatus";
import { newestSelection, parseReportSelection, selectionExists, type ReportSelection } from "@/lib/reports/reportSelection";

type SelectedReportContextValue = {
  selection: ReportSelection | null;
  report: FullReportResponse | null;
  availableSeasons: SeasonOption[];
  availableGameweeks: GameweekOption[];
  newestAvailable: ReportSelection | null;
  isLoadingIndex: boolean;
  isLoadingReport: boolean;
  isMissingReport: boolean;
  isCurrentReport: boolean;
  error: Error | null;
  setSeason: (season: string) => void;
  setGameweek: (gameweek: number) => void;
  retry: () => void;
};

const SelectedReportContext = createContext<SelectedReportContextValue | null>(null);

function keyOf(selection: ReportSelection | null): string | null {
  return selection ? `${selection.season}:${selection.gameweek}` : null;
}

export function ReportSelectionProvider({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const isReportPage = ["/", "/dashboard", "/reports", "/suggested-team", "/captaincy", "/transfers", "/expert-consensus"].includes(pathname);
  const router = useRouter();
  const searchParams = useSearchParams();
  const query = searchParams.toString();
  const requestedSelection = useMemo(() => parseReportSelection(new URLSearchParams(query)), [query]);
  const hasExplicitSelection = searchParams.has("season") || searchParams.has("gameweek");
  const [availableSeasons, setAvailableSeasons] = useState<SeasonOption[]>([]);
  const [defaultSelection, setDefaultSelection] = useState<ReportSelection | null>(null);
  const [currentGameweek, setCurrentGameweek] = useState<number | null>(null);
  const [currentSeason, setCurrentSeason] = useState<string | null>(null);
  const [recommendationsAvailable, setRecommendationsAvailable] = useState(false);
  const [reportState, setReportState] = useState<{ key: string; data: FullReportResponse } | null>(null);
  const [settledReportKey, setSettledReportKey] = useState<string | null>(null);
  const [isLoadingIndex, setIsLoadingIndex] = useState(true);
  const [isLoadingReport, setIsLoadingReport] = useState(false);
  const [indexError, setIndexError] = useState<Error | null>(null);
  const [reportError, setReportError] = useState<Error | null>(null);
  const [retryCount, setRetryCount] = useState(0);

  const replaceSelection = useCallback((selection: ReportSelection) => {
    const params = new URLSearchParams(query);
    params.set("season", selection.season);
    params.set("gameweek", String(selection.gameweek));
    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
  }, [pathname, query, router]);

  useEffect(() => {
    if (!isReportPage) {
      setIsLoadingIndex(false);
      return;
    }
    let active = true;
    setIsLoadingIndex(true);
    setIndexError(null);
    Promise.allSettled([getAvailableGameweeks(), getCurrentGameweek()]).then(([indexResult, currentResult]) => {
      if (!active) return;
      if (indexResult.status === "rejected") {
        setIndexError(indexResult.reason instanceof Error ? indexResult.reason : new Error("Could not load available reports"));
        setAvailableSeasons([]);
        return;
      }
      const seasons = indexResult.value.seasons;
      setAvailableSeasons(seasons);
      const current = currentResult.status === "fulfilled" ? currentResult.value : null;
      const officialGameweek = current?.gameweek ?? null;
      const officialSeason = current?.recommendations_available && officialGameweek != null
        ? seasons.find((item) => item.gameweeks.some((option) => option.gameweek === officialGameweek))?.season ?? null
        : null;
      setCurrentGameweek(officialGameweek);
      setCurrentSeason(officialSeason);
      setRecommendationsAvailable(Boolean(current?.recommendations_available));

    }).finally(() => { if (active) setIsLoadingIndex(false); });
    return () => { active = false; };
  }, [isReportPage, retryCount]);

  useEffect(() => {
    if (!isReportPage || isLoadingIndex || indexError || hasExplicitSelection) return;
    const currentSelection = currentSeason && currentGameweek != null && recommendationsAvailable
      ? { season: currentSeason, gameweek: currentGameweek }
      : null;
    const resolved = currentSelection && selectionExists(availableSeasons, currentSelection)
      ? currentSelection
      : newestSelection(availableSeasons);
    setDefaultSelection(resolved);
    if (resolved) replaceSelection(resolved);
  }, [availableSeasons, currentGameweek, currentSeason, hasExplicitSelection, indexError, isLoadingIndex, isReportPage, recommendationsAvailable, replaceSelection]);

  const selection = hasExplicitSelection ? requestedSelection : defaultSelection;
  const validSelection = Boolean(selection && selectionExists(availableSeasons, selection));
  const malformedSelection = Boolean(hasExplicitSelection && selection
    && (!selection.season || !Number.isInteger(selection.gameweek)));

  useEffect(() => {
    if (isLoadingIndex || indexError || !selection || !validSelection) {
      setIsLoadingReport(false);
      return;
    }
    let active = true;
    const reportKey = keyOf(selection)!;
    setIsLoadingReport(true);
    setReportError(null);
    getSelectedReport(selection.season, selection.gameweek)
      .then((data) => { if (active) setReportState({ key: reportKey, data }); })
      .catch((reason: unknown) => {
        if (!active) return;
        if (!(reason instanceof ApiError && reason.status === 404)) {
          setReportError(reason instanceof Error ? reason : new Error("Could not load report"));
        }
      })
      .finally(() => {
        if (active) {
          setSettledReportKey(reportKey);
          setIsLoadingReport(false);
        }
      });
    return () => { active = false; };
  }, [indexError, isLoadingIndex, retryCount, selection, validSelection]);

  const setSeason = useCallback((season: string) => {
    const option = availableSeasons.find((item) => item.season === season);
    if (!option?.gameweeks.length) return;
    const currentOption = season === currentSeason
      ? option.gameweeks.find((item) => item.gameweek === currentGameweek)
      : undefined;
    const newest = [...option.gameweeks].sort((a, b) => Date.parse(b.last_updated_at) - Date.parse(a.last_updated_at) || b.gameweek - a.gameweek)[0];
    replaceSelection({ season, gameweek: currentOption?.gameweek ?? newest.gameweek });
  }, [availableSeasons, currentGameweek, currentSeason, replaceSelection]);

  const setGameweek = useCallback((gameweek: number) => {
    if (selection && Number.isInteger(gameweek)) replaceSelection({ ...selection, gameweek });
  }, [replaceSelection, selection]);

  const selectedKey = keyOf(selection);
  const report = reportState?.key === selectedKey ? reportState.data : null;
  const reportPending = Boolean(validSelection && selectedKey !== settledReportKey) || isLoadingReport;
  const hasNoPublishedReports = !isLoadingIndex && !indexError && availableSeasons.length === 0;
  const isMissingReport = hasNoPublishedReports || (!isLoadingIndex && !indexError && Boolean(selection)
    && (malformedSelection || !validSelection || (!reportPending && !report && !reportError)));
  const value = useMemo<SelectedReportContextValue>(() => ({
    selection,
    report,
    availableSeasons,
    availableGameweeks: availableSeasons.find((item) => item.season === selection?.season)?.gameweeks ?? [],
    newestAvailable: newestSelection(availableSeasons),
    isLoadingIndex,
    isLoadingReport: reportPending,
    isMissingReport,
    isCurrentReport: isCurrentSelection(selection, currentGameweek, currentSeason, recommendationsAvailable),
    error: indexError ?? reportError,
    setSeason,
    setGameweek,
    retry: () => setRetryCount((value) => value + 1)
  }), [availableSeasons, currentGameweek, currentSeason, indexError, isLoadingIndex, isMissingReport, recommendationsAvailable, report, reportError, reportPending, selection, setGameweek, setSeason]);

  return <SelectedReportContext.Provider value={value}>{children}</SelectedReportContext.Provider>;
}

export function useSelectedReport(): SelectedReportContextValue {
  const context = useContext(SelectedReportContext);
  if (!context) throw new Error("useSelectedReport must be used within ReportSelectionProvider");
  return context;
}
