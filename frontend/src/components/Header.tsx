import Link from "next/link";
import { setLang } from "@/app/actions";
import { Stamp } from "@/components/Stamp";
import { ThemeControl } from "@/components/ThemeControl";
import { type Lang, type Theme, t } from "@/lib/i18n";

export function Header({ lang, theme, signedIn, staff }: { lang: Lang; theme: Theme; signedIn: boolean; staff: boolean }) {
  const d = t(lang);
  const links = (
    <>
      <Link href="/finder">{d.finder}</Link>
      <Link href="/schemes">{d.schemes}</Link>
      <Link href="/donate">{d.donate}</Link>
      {staff && <Link href="/admin">{d.staffArea}</Link>}
      <Link href={signedIn ? "/account" : "/login"}>{signedIn ? d.account : d.login}</Link>
    </>
  );
  return (
    <header className="site">
      <a href="#main" className="skip">{d.skip}</a>
      <div className="wrap bar">
        <Link href="/" className="brand"><Stamp />{d.siteName}</Link>
        <nav className="main" aria-label={d.menu}>{links}</nav>
        <div className="controls">
          <form action={setLang}>
            <input type="hidden" name="lang" value={lang === "hi" ? "en" : "hi"} />
            <button type="submit" aria-label={d.language} lang={lang === "hi" ? "en" : "hi"}>
              {lang === "hi" ? "English" : "हिन्दी"}
            </button>
          </form>
          <span className="desktop-only"><ThemeControl d={d} theme={theme} name="theme-top" /></span>
          <details className="menu">
            <summary>{d.menu}</summary>
            <div className="menu-panel">
              <nav className="menu-links" aria-label={d.menu}>{links}</nav>
              <ThemeControl d={d} theme={theme} name="theme-menu" />
            </div>
          </details>
        </div>
      </div>
    </header>
  );
}
