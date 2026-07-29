import * as React from "react";

export type ReportUnavailableStateProps = {
  title?: string;
  message?: string;
  action?: React.ReactNode;
};

/**
 * Displayed when the backend has no report for the requested season/gameweek.
 * This is distinct from an API error — the request succeeded but returned nothing.
 */
export function ReportUnavailableState({
  title = "Report not available",
  message = "There isn't a published report for the selected gameweek yet. Try a different gameweek or check back closer to the deadline.",
  action,
}: ReportUnavailableStateProps) {
  return (
    <div className="kasifpl-state" role="status">
      <h2 className="kasifpl-state__title">{title}</h2>
      <p className="kasifpl-state__body">{message}</p>
      {action ? <div className="kasifpl-state__actions">{action}</div> : null}
    </div>
  );
}
