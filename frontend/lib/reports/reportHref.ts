import type { ReportSelection } from "./reportSelection";

export function reportHref(path: string, selection: ReportSelection | null): string {
  if (!selection || !selection.season || !Number.isInteger(selection.gameweek)) return path;
  const [pathnameAndQuery, hash] = path.split("#", 2);
  const [pathname, existingQuery] = pathnameAndQuery.split("?", 2);
  const params = new URLSearchParams(existingQuery ?? "");
  params.set("season", selection.season);
  params.set("gameweek", String(selection.gameweek));
  return `${pathname}?${params.toString()}${hash ? `#${hash}` : ""}`;
}
