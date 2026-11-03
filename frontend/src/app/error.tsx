"use client";

import { useSyncExternalStore } from "react";

const TEXT = {
  hi: { title: "कुछ गड़बड़ हो गई", body: "यह पेज अभी नहीं खुल सका। आपका कोई दान या जानकारी प्रभावित नहीं हुई।", retry: "फिर कोशिश करें" },
  en: { title: "Something went wrong", body: "This page could not open. No donation or information was affected.", retry: "Try again" },
};

export default function ErrorPage({ retry }: { error: unknown; retry: () => void }) {
  const lang = useSyncExternalStore(() => () => {}, () => (document.documentElement.lang === "en" ? "en" : "hi"), () => "hi" as const);
  const d = TEXT[lang];
  return (
    <section className="wrap page stack" role="alert">
      <h1>{d.title}</h1>
      <p>{d.body}</p>
      <p><button type="button" className="primary" onClick={() => retry()}>{d.retry}</button></p>
    </section>
  );
}
