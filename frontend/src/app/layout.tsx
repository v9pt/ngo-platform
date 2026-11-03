import type { Metadata } from "next";
import { Header } from "@/components/Header";
import { getMe } from "@/lib/api";
import { getLang, getTheme, t } from "@/lib/i18n";
import "./globals.css";

export const metadata: Metadata = {
  title: "Mahila Vikas Trust",
  description: "Find government schemes for women, and support our work.",
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const [lang, theme, me] = await Promise.all([getLang(), getTheme(), getMe()]);
  return (
    <html lang={lang} data-theme={theme === "system" ? undefined : theme}>
      <body>
        <Header lang={lang} theme={theme} signedIn={me !== null} />
        <main className="wrap">{children}</main>
        <footer className="site">
          <div className="wrap">{t(lang).sampleNote}</div>
        </footer>
      </body>
    </html>
  );
}
