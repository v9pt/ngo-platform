/** One block-print stamp, the identity mark used for the logo and the finder's progress. */
export function Stamp({ className, label }: { className?: string; label?: string }) {
  return (
    <svg viewBox="0 0 32 32" fill="currentColor" className={className} role={label ? "img" : undefined}
         aria-label={label} aria-hidden={label ? undefined : true}>
      <path d="M16 2c3 4 3 8 0 12-3-4-3-8 0-12z" /><path d="M16 30c-3-4-3-8 0-12 3 4 3 8 0 12z" />
      <path d="M2 16c4-3 8-3 12 0-4 3-8 3-12 0z" /><path d="M30 16c-4 3-8 3-12 0 4-3 8-3 12 0z" />
      <path d="M6 6c5 0 8 3 8 8-5 0-8-3-8-8z" /><path d="M26 6c0 5-3 8-8 8 0-5 3-8 8-8z" />
      <path d="M6 26c0-5 3-8 8-8 0 5-3 8-8 8z" /><path d="M26 26c-5 0-8-3-8-8 5 0 8 3 8 8z" />
    </svg>
  );
}
