import Link from "next/link";

export function StaffNav({ role, current }: { role: string; current: "schemes" | "callbacks" | "reports" }) {
  const items: [typeof current, string, string][] = [
    ["schemes", "Schemes", "/admin"],
    ["callbacks", "Call-backs", "/admin/callbacks"],
    ...(role === "admin" ? ([["reports", "Campaign reports", "/admin/reports"]] as [typeof current, string, string][]) : []),
  ];
  return (
    <nav className="staff-nav" aria-label="Staff">
      {items.map(([key, label, href]) => (
        <Link key={key} className="chip" href={href} aria-current={current === key ? "true" : undefined}>{label}</Link>
      ))}
    </nav>
  );
}
