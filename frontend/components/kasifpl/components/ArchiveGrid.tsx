import * as React from "react";
import type { ArchiveEntry } from "../types";
import { formatDeadline } from "./_shared";
import { SectionUnavailableState } from "./SectionUnavailableState";

export type ArchiveGridProps = {
  entries?: ArchiveEntry[];
  title?: string;
  subtitle?: string;
  renderLink?: (props: {
    href: string;
    className?: string;
    children: React.ReactNode;
  }) => React.ReactNode;
};

const defaultRender: NonNullable<ArchiveGridProps["renderLink"]> = (p) => (
  <a {...p} />
);

export function ArchiveGrid({
  entries,
  title = "Report archive",
  subtitle,
  renderLink = defaultRender,
}: ArchiveGridProps) {
  const items = entries ?? [];
  return (
    <section className="kasifpl-section" aria-label={title}>
      <h2 className="kasifpl-section__title">{title}</h2>
      {subtitle ? <p className="kasifpl-section__subtitle">{subtitle}</p> : null}
      {items.length === 0 ? (
        <SectionUnavailableState message="No archived reports available." />
      ) : (
        <div className="kasifpl-grid kasifpl-grid--cols-3">
          {items.map((e) =>
            renderLink({
              key: `${e.season}-${e.gameweek}`,
              href: e.href,
              className: "kasifpl-archive-card",
              children: (
                <>
                  <div className="kasifpl-archive-card__head">
                    <div className="kasifpl-archive-card__gw">
                      GW {e.gameweek} <span style={{ color: "var(--kasifpl-color-fg-muted)", fontSize: "0.75rem", fontWeight: 500 }}>{e.season}</span>
                    </div>
                    {e.isCurrent ? <span className="kasifpl-chip kasifpl-chip--strong">Current</span> : null}
                  </div>
                  {e.deadline ? <div className="kasifpl-archive-card__deadline">Deadline {formatDeadline(e.deadline)}</div> : null}
                  {e.title ? <div className="kasifpl-archive-card__title">{e.title}</div> : null}
                  {e.summary ? <div className="kasifpl-archive-card__summary">{e.summary}</div> : null}
                </>
              ),
            } as never),
          )}
        </div>
      )}
    </section>
  );
}
