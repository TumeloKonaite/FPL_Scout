"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Icon, type IconName } from "./Icons";

const navItems = [
  { href: "/dashboard", label: "This Gameweek", icon: "dashboard" },
  { href: "/reports", label: "Reports", icon: "reports" },
  { href: "/suggested-team", label: "Suggested Team", icon: "team" },
  { href: "/captaincy", label: "Captaincy", icon: "captain" },
  { href: "/transfers", label: "Transfers", icon: "transfers" },
  { href: "/expert-consensus", label: "Expert Consensus", icon: "experts" }
] satisfies { href: string; label: string; icon: IconName }[];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="sidebar" aria-label="Primary navigation">
      <Link className="sidebar-brand" href="/">
        <span className="brand-mark"><span>FT</span></span>
        <span className="brand-copy"><strong>FPL Technocrat</strong><small>Gameweek intelligence</small></span>
      </Link>
      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <Link className={`sidebar-link ${pathname === item.href || (pathname === "/" && item.href === "/dashboard") ? "active" : ""}`} href={item.href} key={item.href}>
            <Icon name={item.icon} />
            <span>{item.label}</span>
          </Link>
        ))}
      </nav>
      <div className="sidebar-foot">
        <span className="season-dot" />
        <div><strong>Active season</strong><span>Scout workspace</span></div>
      </div>
    </aside>
  );
}
