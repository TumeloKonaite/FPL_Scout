import type { ReactNode, SVGProps } from "react";

export type IconName =
  | "dashboard"
  | "reports"
  | "team"
  | "captain"
  | "transfers"
  | "experts"
  | "pipeline"
  | "arrow"
  | "spark"
  | "alert";

const paths: Record<IconName, ReactNode> = {
  dashboard: <><rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/></>,
  reports: <><path d="M6 3h9l4 4v14H6z"/><path d="M14 3v5h5M9 13h6M9 17h6"/></>,
  team: <><circle cx="9" cy="8" r="3"/><circle cx="17" cy="9" r="2.5"/><path d="M3 20c.4-4 2.5-6 6-6s5.6 2 6 6M14 15c3.8-.6 6.2 1.1 7 4"/></>,
  captain: <><path d="M12 3l2.3 4.7 5.2.8-3.8 3.7.9 5.2-4.6-2.5-4.6 2.5.9-5.2-3.8-3.7 5.2-.8z"/></>,
  transfers: <><path d="M4 8h13M14 5l3 3-3 3M20 16H7M10 13l-3 3 3 3"/></>,
  experts: <><circle cx="12" cy="8" r="4"/><path d="M5 21c.5-4.5 2.8-7 7-7s6.5 2.5 7 7M4 7v5M20 7v5"/></>,
  pipeline: <><circle cx="5" cy="5" r="2"/><circle cx="19" cy="5" r="2"/><circle cx="12" cy="19" r="2"/><path d="M7 5h10M6.3 6.5l4.5 10.6M17.7 6.5l-4.5 10.6"/></>,
  arrow: <><path d="M5 12h14M15 8l4 4-4 4"/></>,
  spark: <><path d="M12 2l1.6 5.4L19 9l-5.4 1.6L12 16l-1.6-5.4L5 9l5.4-1.6zM19 16l.7 2.3L22 19l-2.3.7L19 22l-.7-2.3L16 19l2.3-.7z"/></>,
  alert: <><path d="M12 3L2.8 20h18.4z"/><path d="M12 9v5M12 17.5v.1"/></>
};

export function Icon({ name, ...props }: SVGProps<SVGSVGElement> & { name: IconName }) {
  return (
    <svg aria-hidden="true" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" viewBox="0 0 24 24" {...props}>
      {paths[name]}
    </svg>
  );
}
