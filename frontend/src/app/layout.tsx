import type { Metadata } from "next";
import { Mukta, Yatra_One } from "next/font/google";
import { Header } from "@/components/Header";
import { getMe } from "@/lib/api";
import { getLang, getTheme, t } from "@/lib/i18n";
import "./globals.css";

const mukta = Mukta({ subsets: ["devanagari", "latin"], weight: ["400", "500", "600", "700"], variable: "--font-mukta", display: "swap" });
const yatra = Yatra_One({ subsets: ["devanagari", "latin"], weight: "400", variable: "--font-yatra", display: "swap" });

export const metadata: Metadata = {
  title: { default: "Mahila Vikas Trust", template: "%s | Mahila Vikas Trust" },
  description: "Find the government schemes meant for you, in Hindi, and support women's livelihoods in Bhopal.",
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const [lang, theme, me] = await Promise.all([getLang(), getTheme(), getMe()]);
  const d = t(lang);
  return (
    <html lang={lang} data-theme={theme === "system" ? undefined : theme} className={`${mukta.variable} ${yatra.variable}`}>
      <body>
        <Header lang={lang} theme={theme} signedIn={me !== null} staff={me !== null && me.role !== "donor"} />
        <main id="main" tabIndex={-1}>{children}</main>
        <footer className="site">
          <div className="wrap cols">
            <div>
              <p style={{ fontFamily: "var(--font-display)", fontSize: "1.3rem" }}>{d.siteName}</p>
              <p>{d.place}</p>
              <small>{d.sampleNote}</small>
            </div>
            <div>
              <p>{d.helpline}</p>
              <p style={{ fontWeight: 700 }}>{d.helplineNumber}</p>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
