import * as React from "react";

export type KasiFplPageShellProps = {
  header?: React.ReactNode;
  footer?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
};

/**
 * Page shell. Applies the KasiFPL background and vertical rhythm.
 * Server-safe: no state, no browser APIs.
 */
export function KasiFplPageShell({ header, footer, children, className }: KasiFplPageShellProps) {
  return (
    <div className={["kasifpl-shell", className].filter(Boolean).join(" ")}>
      {header}
      <main className="kasifpl-shell__main">{children}</main>
      {footer}
    </div>
  );
}

export type KasiFplFooterProps = {
  children?: React.ReactNode;
};

export function KasiFplFooter({ children }: KasiFplFooterProps) {
  return <footer className="kasifpl-footer">{children}</footer>;
}
