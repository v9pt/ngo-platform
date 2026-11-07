"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { speechRecognition } from "@/lib/voice";

type Props = {
  lang: "hi" | "en";
  labels: { start: string; stop: string; listening: string; failed: string; unsupported: string };
  onText: (spoken: string) => void;
};

export function VoiceButton({ lang, labels, onText }: Props) {
  const supported = useSyncExternalStore(() => () => {}, () => speechRecognition() !== null, () => false);
  const [listening, setListening] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const rec = useRef<ReturnType<typeof makeRecognition>>(null);

  useEffect(() => {
    return () => rec.current?.stop();
  }, []);

  function makeRecognition() {
    const Ctor = speechRecognition();
    return Ctor ? new Ctor() : null;
  }

  function toggle() {
    if (listening) return rec.current?.stop();
    const r = makeRecognition();
    if (!r) return setMessage(labels.unsupported);
    r.lang = lang === "hi" ? "hi-IN" : "en-IN";
    r.interimResults = false;
    r.maxAlternatives = 1;
    r.onresult = (e) => onText(e.results[0]?.[0]?.transcript ?? "");
    r.onerror = () => setMessage(labels.failed);
    r.onend = () => setListening(false);
    rec.current = r;
    setMessage(null);
    setListening(true);
    r.start();
  }

  if (!supported) return null;
  return (
    <>
      <button type="button" aria-pressed={listening} onClick={toggle}>
        {listening ? labels.stop : labels.start}
      </button>
      <span role="status" className="hint" style={{ display: "inline", marginLeft: "0.5rem" }}>
        {listening ? labels.listening : message}
      </span>
    </>
  );
}
