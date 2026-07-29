"use client";

import * as React from "react";

export type ApiErrorStateProps = {
  title?: string;
  message?: string;
  /** Raw error detail rendered below the message for diagnosis. */
  detail?: string | null;
  onRetry?: () => void;
  retryLabel?: string;
};

export function ApiErrorState({
  title = "We couldn't load this report",
  message = "The report service didn't respond as expected. Please try again in a moment.",
  detail,
  onRetry,
  retryLabel = "Try again",
}: ApiErrorStateProps) {
  return (
    <div className="kasifpl-state kasifpl-state--error" role="alert">
      <h2 className="kasifpl-state__title">{title}</h2>
      <p className="kasifpl-state__body">{message}</p>
      {detail ? (
        <pre style={{
          marginTop: 12, padding: 12, textAlign: "left",
          background: "rgba(0,0,0,0.35)", borderRadius: 8,
          fontFamily: "var(--kasifpl-font-mono)", fontSize: "0.75rem",
          color: "var(--kasifpl-color-fg-muted)",
          overflowX: "auto",
        }}>{detail}</pre>
      ) : null}
      {onRetry ? (
        <div className="kasifpl-state__actions">
          <button type="button" className="kasifpl-btn kasifpl-btn--primary" onClick={onRetry}>{retryLabel}</button>
        </div>
      ) : null}
    </div>
  );
}
