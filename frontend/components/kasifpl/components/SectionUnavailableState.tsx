import * as React from "react";

export type SectionUnavailableStateProps = {
  title?: string;
  message: string;
};

/** Small inline unavailable notice used inside sections. Neutral tone. */
export function SectionUnavailableState({ title, message }: SectionUnavailableStateProps) {
  return (
    <div className="kasifpl-state" role="status" style={{ padding: "20px 16px" }}>
      {title ? <h3 className="kasifpl-state__title" style={{ fontSize: "1rem" }}>{title}</h3> : null}
      <p className="kasifpl-state__body" style={{ fontSize: "0.875rem" }}>{message}</p>
    </div>
  );
}
