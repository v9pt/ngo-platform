import Link from "next/link";

/** An empty screen is an invitation to act, so it always carries the next step. */
export function Empty({ text, href, action }: { text: string; href?: string; action?: string }) {
  return (
    <div className="empty">
      <p>{text}</p>
      {href && action && <p><Link className="btn primary" href={href}>{action}</Link></p>}
    </div>
  );
}

export function LoadFailed({ text }: { text: string }) {
  return <p className="notice error" role="alert">{text}</p>;
}

export function PageSkeleton({ label }: { label: string }) {
  return (
    <div className="wrap page" role="status" aria-label={label}>
      <div className="skeleton" style={{ height: "2.6rem", maxWidth: "24rem" }} />
      <div className="skeleton" style={{ height: "1.2rem", maxWidth: "36rem", marginTop: "1rem" }} />
      {[0, 1, 2, 3].map((i) => <div key={i} className="skeleton" style={{ height: "4.5rem", marginTop: "1rem" }} />)}
    </div>
  );
}
