"use client";

import * as React from "react";
import type { NavItem, NavPage } from "../types";

export type KasiFplHeaderProps = {
  brand?: React.ReactNode;
  brandHref?: string;
  navItems: NavItem[];
  activePage?: NavPage;
  /** Optional slot rendered at the far right (e.g. auth menu). */
  rightSlot?: React.ReactNode;
  /**
   * Render prop for links so the host can inject Next.js <Link>.
   * If omitted, plain <a href> is used.
   */
  renderLink?: (props: {
    href: string;
    className?: string;
    "aria-current"?: "page";
    children: React.ReactNode;
    onClick?: () => void;
  }) => React.ReactNode;
};

const defaultRender: NonNullable<KasiFplHeaderProps["renderLink"]> = (props) => (
  <a {...props} />
);

export function KasiFplHeader({
  brand,
  brandHref = "/",
  navItems,
  activePage,
  rightSlot,
  renderLink = defaultRender,
}: KasiFplHeaderProps) {
  const [open, setOpen] = React.useState(false);

  const brandNode =
    brand ??
    renderLink({
      href: brandHref,
      className: "kasifpl-header__brand",
      children: (
        <>
          <span className="kasifpl-header__brand-mark" aria-hidden>K</span>
          <span>KasiFPL</span>
        </>
      ),
    });

  return (
    <header className="kasifpl-header">
      <div className="kasifpl-header__inner">
        {brandNode}
        <nav className="kasifpl-header__nav" aria-label="Primary">
          {navItems.map((item) =>
            renderLink({
              key: item.key,
              href: item.href,
              className: "kasifpl-header__nav-link",
              "aria-current": activePage === item.key ? "page" : undefined,
              children: item.label,
            } as never),
          )}
        </nav>
        {rightSlot ? <div className="kasifpl-header__right">{rightSlot}</div> : null}
        <button
          type="button"
          className="kasifpl-header__toggle"
          aria-expanded={open}
          aria-controls="kasifpl-mobile-nav"
          aria-label={open ? "Close menu" : "Open menu"}
          onClick={() => setOpen((v) => !v)}
        >
          {open ? "Close" : "Menu"}
        </button>
      </div>
      <div id="kasifpl-mobile-nav" className="kasifpl-header__mobile" data-open={open}>
        {navItems.map((item) =>
          renderLink({
            key: `m-${item.key}`,
            href: item.href,
            className: "kasifpl-header__nav-link",
            "aria-current": activePage === item.key ? "page" : undefined,
            onClick: () => setOpen(false),
            children: item.label,
          } as never),
        )}
      </div>
    </header>
  );
}
