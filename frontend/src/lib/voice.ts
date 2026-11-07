/** Joins a spoken phrase onto what is already typed, capped to the textarea limit. */
export function appendSpoken(current: string, spoken: string, max = 500): string {
  const heard = spoken.trim();
  if (!heard) return current;
  const base = current.trim();
  return (base ? `${base} ${heard}` : heard).slice(0, max);
}

type Recognition = {
  lang: string;
  interimResults: boolean;
  maxAlternatives: number;
  onresult: ((e: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onerror: ((e: { error: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
};

/** The browser's speech recogniser, or null where it is not offered (Firefox, some phones). */
export function speechRecognition(): (new () => Recognition) | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as Record<string, unknown>;
  return (w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null) as (new () => Recognition) | null;
}
