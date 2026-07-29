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
    <div className="kasifpl-page">
      <div className="kasifpl-page__heading-row">
        <div className="kasifpl-page__heading">
          {eyebrow ? <span className="kasifpl-page__eyebrow">{eyebrow}</span> : null}
          <h1>{title}</h1>
          <p>{description}</p>
        </div>
        {action ? <div className="kasifpl-page__action">{action}</div> : null}
      </div>
      {children}
    </div>
  );
}
