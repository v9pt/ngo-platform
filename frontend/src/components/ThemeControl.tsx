"use client";

import { useState } from "react";
import type { Dict, Theme } from "@/lib/i18n";

const ICONS: Record<Theme, React.ReactNode> = {
  system: <path d="M3 5h18v11H3zM8 20h8M12 16v4" fill="none" stroke="currentColor" strokeWidth="2" />,
  light: <><circle cx="12" cy="12" r="4.5" /><path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M5 19l2-2M17 7l2-2" stroke="currentColor" strokeWidth="2" /></>,
  dark: <path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a7 7 0 0 0 10.5 10.5z" />,
};

function rememberTheme(value: Theme) {
  document.cookie = `theme=${value}; path=/; max-age=31536000; samesite=lax`;
}

/** Three states, applied at once. A cookie lets the server render the right theme with no flash. */
export function ThemeControl({ d, theme, name }: { d: Dict; theme: Theme; name: string }) {
  const [current, setCurrent] = useState<Theme>(theme);
  function choose(next: Theme) {
    setCurrent(next);
    if (next === "system") document.documentElement.removeAttribute("data-theme");
    else document.documentElement.setAttribute("data-theme", next);
    rememberTheme(next);
  }
  const options: [Theme, string][] = [["system", d.themeSystem], ["light", d.themeLight], ["dark", d.themeDark]];
  return (
    <fieldset className="theme">
      <legend className="visually-hidden">{d.theme}</legend>
      {options.map(([value, label]) => (
        <label key={value} title={label}>
          <input type="radio" name={name} checked={current === value} onChange={() => choose(value)} />
          <span className="visually-hidden">{label}</span>
          <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">{ICONS[value]}</svg>
        </label>
      ))}
    </fieldset>
  );
}
