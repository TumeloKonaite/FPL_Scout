import type { ReactNode } from "react";

type PageShellProps = {
  title: string;
  description: string;
  children: ReactNode;
  eyebrow?: string;
  action?: ReactNode;
};

export function PageShell({ title, description, children, eyebrow, action }: PageShellProps) {
  return (
    <div className="page-shell">
      <div className="page-heading-row">
        <div className="page-heading">
          {eyebrow ? <span className="eyebrow">{eyebrow}</span> : null}
          <h1>{title}</h1>
          <p>{description}</p>
        </div>
        {action ? <div className="page-action">{action}</div> : null}
      </div>
      {children}
    </div>
  );
}
