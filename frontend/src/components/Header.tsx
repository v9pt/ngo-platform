import Link from "next/link";
import { setLang, setTheme } from "@/app/actions";
import { type Lang, type Theme, t } from "@/lib/i18n";

export function Header({ lang, theme }: { lang: Lang; theme: Theme }) {
  const d = t(lang);
  return (
    <header className="site">
      <div className="wrap">
        <Link href="/" className="brand">{d.siteName}</Link>
        <nav aria-label="Main">
          <Link href="/schemes">{d.schemes}</Link>
          <Link href="/finder">{d.finder}</Link>
        </nav>
        <div className="controls">
          <form action={setLang}>
            <input type="hidden" name="lang" value={lang === "hi" ? "en" : "hi"} />
            <button type="submit" aria-label={d.language} lang={lang === "hi" ? "en" : "hi"}>
              {lang === "hi" ? "English" : "हिन्दी"}
            </button>
          </form>
          <form action={setTheme}>
            <label className="muted" htmlFor="theme-select">{d.theme}</label>{" "}
            <select id="theme-select" name="theme" defaultValue={theme} style={{ width: "auto" }}>
              <option value="system">{d.themeSystem}</option>
              <option value="light">{d.themeLight}</option>
              <option value="dark">{d.themeDark}</option>
            </select>{" "}
            <button type="submit">OK</button>
          </form>
        </div>
      </div>
    </header>
  );
}
