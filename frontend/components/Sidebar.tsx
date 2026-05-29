import Link from "next/link";

const navItems = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/reports", label: "Reports" },
  { href: "/suggested-team", label: "Suggested Team" },
  { href: "/captaincy", label: "Captaincy" },
  { href: "/transfers", label: "Transfers" },
  { href: "/expert-consensus", label: "Expert Consensus" },
  { href: "/pipeline-runner", label: "Pipeline Runner" }
];

export function Sidebar() {
  return (
    <aside className="sidebar" aria-label="Primary navigation">
      <Link className="sidebar-brand" href="/">
        <strong>FPL Technocrat</strong>
        <span>Gameweek intelligence</span>
      </Link>
      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <Link className="sidebar-link" href={item.href} key={item.href}>
            {item.label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
