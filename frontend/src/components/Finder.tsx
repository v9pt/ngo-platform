"use client";

import Link from "next/link";
import { useState } from "react";
import { VoiceButton } from "./VoiceButton";
import { appendSpoken } from "@/lib/voice";
import { Callback } from "@/components/Callback";
import { Stamp } from "@/components/Stamp";
import type { SchemeCheck } from "@/lib/api";
import {
  type AnswerKey, type Answers, DISTRICTS, MARITAL, type Marital, ageError, describeRule, districtName,
  fromSuggestion, needName, toPayload, visibleQuestions,
} from "@/lib/finder";
import { fill } from "@/lib/format";
import type { Dict, Lang } from "@/lib/i18n";

type Stage = "start" | "ask" | "review" | "results";
type Reading = { source: "ai" | "rules"; unsure: AnswerKey[] } | null;

export function Finder({ d, lang, skipStart = false }: { d: Dict; lang: Lang; skipStart?: boolean }) {
  const [stage, setStage] = useState<Stage>(skipStart ? "ask" : "start");
  const [answers, setAnswers] = useState<Answers>({});
  const [step, setStep] = useState(0);
  const [text, setText] = useState("");
  const [ageDraft, setAgeDraft] = useState("");
  const [reading, setReading] = useState<Reading>(null);
  const [results, setResults] = useState<SchemeCheck[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const questions = visibleQuestions(answers);
  const question = questions[Math.min(step, questions.length - 1)];
  const qText = (q: { hi: string; en: string }) => q[lang];

  function setAnswer<K extends AnswerKey>(key: K, value: Answers[K] | undefined) {
    setAnswers((a) => {
      const next = { ...a };
      if (value === undefined) delete next[key];
      else next[key] = value;
      return next;
    });
    setReading((r) => (r ? { ...r, unsure: r.unsure.filter((k) => k !== key) } : r));
  }

  function advance() {
    setError(null);
    if (step >= visibleQuestions(answers).length - 1) setStage("review");
    else setStep((s) => s + 1);
  }

  function choose<K extends AnswerKey>(key: K, value: Answers[K] | undefined) {
    const next = { ...answers };
    if (value === undefined) delete next[key];
    else next[key] = value;
    setAnswers(next);
    if (step >= visibleQuestions(next).length - 1) setStage("review");
    else setStep((s) => s + 1);
  }

  function restart() {
    setAnswers({}); setStep(0); setText(""); setAgeDraft(""); setReading(null); setResults(null); setError(null);
    setStage(skipStart ? "ask" : "start");
  }

  async function readText(e: React.FormEvent) {
    e.preventDefault();
    if (text.trim().length < 3) return setError(d.typeEmpty);
    setBusy(true);
    setError(null);
    try {
      const r = await fetch("/api/v1/schemes/interpret", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: text.trim() }),
      });
      if (!r.ok) throw new Error(String(r.status));
      const out = (await r.json()) as { answers: Record<string, unknown>; unsure: AnswerKey[]; source: "ai" | "rules" };
      const suggested = fromSuggestion(out.answers);
      setAnswers(suggested);
      setAgeDraft(suggested.age === undefined ? "" : String(suggested.age));
      setReading({ source: out.source, unsure: out.unsure });
      setStage("review");
    } catch {
      // Reading is a convenience. If it fails, the questions still work.
      setError(d.readError);
      setStage("ask");
    } finally {
      setBusy(false);
    }
  }

  async function check(e?: React.FormEvent) {
    e?.preventDefault();
    if (ageError(ageDraft, lang)) return setError(ageError(ageDraft, lang));
    setBusy(true);
    setError(null);
    try {
      const r = await fetch("/api/v1/schemes/check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(toPayload(answers)),
      });
      if (!r.ok) throw new Error(String(r.status));
      setResults((await r.json()) as SchemeCheck[]);
      setStage("results");
    } catch {
      setError(d.loadError);
    } finally {
      setBusy(false);
    }
  }

  const errorBox = error && <p className="notice error" role="alert" style={{ marginBottom: "1rem" }}>{error}</p>;

  if (stage === "start") {
    return (
      <div className="finder-panel">
        <form onSubmit={readText} noValidate>
          {errorBox}
          <div className="field">
            <label htmlFor="situation" className="question" style={{ display: "block" }}>{d.typeLabel}</label>
            <textarea id="situation" rows={3} maxLength={500} value={text} onChange={(e) => setText(e.target.value)}
                      placeholder={d.typeHint} aria-describedby="privacy" />
          </div>
          <div className="row" style={{ marginTop: "0.75rem" }}>
            <button type="submit" className="primary" disabled={busy}>{busy ? d.reading : d.typeSubmit}</button>
            <button type="button" onClick={() => { setError(null); setStage("ask"); }}>{d.startQuestions}</button>
            <VoiceButton lang={lang} onText={(t) => setText((cur) => appendSpoken(cur, t))}
              labels={{ start: d.voiceStart, stop: d.voiceStop, listening: d.voiceListening, failed: d.voiceFailed, unsupported: d.voiceFailed }} />
          </div>
          <small id="privacy" className="hint">{d.privacy}</small>
        </form>
      </div>
    );
  }

  if (stage === "ask") {
    const answered = step;
    return (
      <div className="finder-panel">
        {errorBox}
        <div className="stamps" role="img" aria-label={`${d.questionOf} ${step + 1} ${d.of} ${questions.length}`}>
          {questions.map((q, i) => (
            <Stamp key={q.key} className={i < answered ? (i === answered - 1 ? "on last" : "on") : undefined} />
          ))}
        </div>
        <p className="muted" aria-hidden="true">{step + 1} / {questions.length}</p>
        {question.kind === "age" ? (
          <form onSubmit={(e) => {
            e.preventDefault();
            const problem = ageError(ageDraft, lang);
            if (problem) return setError(problem);
            setAnswer("age", ageDraft.trim() === "" ? undefined : Number(ageDraft));
            advance();
          }} noValidate>
            <label htmlFor="age" className="question" style={{ display: "block" }}>{qText(question)}</label>
            <input id="age" type="number" inputMode="numeric" min={0} max={120} value={ageDraft} autoFocus
                   style={{ maxWidth: "10rem" }} onChange={(e) => setAgeDraft(e.target.value)}
                   aria-invalid={Boolean(error)} />
            <div className="finder-nav">
              <button type="submit" className="primary">{d.next}</button>
              <button type="button" className="link" onClick={() => { setAgeDraft(""); setAnswer("age", undefined); advance(); }}>{d.skipQ}</button>
            </div>
          </form>
        ) : (
          <>
            <h2 className="question" id="q-title">{qText(question)}</h2>
            {question.kind === "yesno" && (
              <div className="answers two" role="group" aria-labelledby="q-title">
                <button type="button" aria-pressed={answers[question.key] === true} onClick={() => choose(question.key, true)}>{d.yes}</button>
                <button type="button" aria-pressed={answers[question.key] === false} onClick={() => choose(question.key, false)}>{d.no}</button>
              </div>
            )}
            {question.kind === "marital" && (
              <div className="answers two" role="group" aria-labelledby="q-title">
                {MARITAL.map((m) => (
                  <button key={m.value} type="button" aria-pressed={answers.marital_status === m.value}
                          onClick={() => choose("marital_status", m.value)}>{m[lang]}</button>
                ))}
              </div>
            )}
            {question.kind === "district" && (
              <div className="answers two" role="group" aria-labelledby="q-title">
                {DISTRICTS.map((x) => (
                  <button key={x} type="button" aria-pressed={answers.district === x}
                          onClick={() => choose("district", x)}>{districtName(x, lang)}</button>
                ))}
              </div>
            )}
            <div className="finder-nav">
              <button type="button" className="link" onClick={() => setStep((s) => Math.max(0, s - 1))} disabled={step === 0}>{d.back}</button>
              <button type="button" className="link" onClick={() => choose(question.key, undefined)}>{d.notSure}</button>
            </div>
          </>
        )}
      </div>
    );
  }

  if (stage === "review") {
    const found = reading ? Object.keys(answers).length : 0;
    return (
      <form className="finder-panel stack" onSubmit={check} noValidate>
        <h2 className="question" style={{ margin: 0 }}>{d.reviewTitle}</h2>
        {reading && (
          <p className={found ? "notice" : "notice warn"} role="status">
            {found === 0 ? d.reviewNothing : reading.source === "ai" ? d.reviewFromAi : d.reviewFromRules}
          </p>
        )}
        {errorBox}
        <div className="review-grid">
          {questions.map((q) => {
            const unsure = reading?.unsure.includes(q.key);
            const hintId = unsure ? `${q.key}-unsure` : undefined;
            return (
              <div key={q.key} className={unsure ? "field unsure" : "field"}>
                <label htmlFor={`r-${q.key}`}>{qText(q)}</label>
                {q.kind === "age" ? (
                  <input id={`r-${q.key}`} type="number" inputMode="numeric" min={0} max={120} value={ageDraft} aria-describedby={hintId}
                         aria-invalid={Boolean(ageError(ageDraft, lang))}
                         onChange={(e) => {
                           setAgeDraft(e.target.value);
                           const bad = e.target.value.trim() === "" || ageError(e.target.value, lang);
                           setAnswer("age", bad ? undefined : Number(e.target.value));
                         }} />
                ) : (
                  <select id={`r-${q.key}`} aria-describedby={hintId} value={selectValue(answers[q.key])}
                          onChange={(e) => {
                            const v = e.target.value;
                            if (q.kind === "yesno") setAnswer(q.key, v === "" ? undefined : (v === "yes") as never);
                            else if (q.key === "marital_status") setAnswer(q.key, (v || undefined) as Marital | undefined);
                            else setAnswer("district", v || undefined);
                          }}>
                    <option value="">{d.notSure}</option>
                    {q.kind === "yesno" && <><option value="yes">{d.yes}</option><option value="no">{d.no}</option></>}
                    {q.kind === "marital" && MARITAL.map((m) => <option key={m.value} value={m.value}>{m[lang]}</option>)}
                    {q.kind === "district" && DISTRICTS.map((x) => <option key={x} value={x}>{districtName(x, lang)}</option>)}
                  </select>
                )}
                {unsure && <small id={hintId} className="hint">{d.unsureNote}</small>}
              </div>
            );
          })}
        </div>
        <div className="finder-nav">
          <button type="submit" className="primary" disabled={busy}>{busy ? d.checking : d.check}</button>
          <button type="button" className="link" onClick={restart}>{d.startOver}</button>
        </div>
      </form>
    );
  }

  const group = (s: SchemeCheck["status"]) => (results ?? []).filter((r) => r.status === s);
  const match = group("match"), possible = group("possible"), excluded = group("excluded");
  const row = (r: SchemeCheck) => (
    <article key={r.code} className="result">
      <div className="result-head">
        <h4 style={{ margin: 0, fontSize: "1.2rem" }}>{lang === "hi" ? r.title_hi : r.title_en}</h4>
        <span className={`tag ${r.status}`}>{d[r.status]}</span>
      </div>
      <p className="benefit">{(lang === "hi" && r.benefit_hi) || r.benefit_en}</p>
      <p className="muted">{needName(r.need, lang)}</p>
      <ul className="reasons">
        {r.rules.map((x, i) => (
          <li key={i}>
            <span className={`mark ${x.outcome}`} aria-hidden="true">{x.outcome === "met" ? "✓" : x.outcome === "not_met" ? "✕" : "?"}</span>
            <span>{describeRule(x, lang)} <span className="muted">({d[x.outcome]})</span></span>
          </li>
        ))}
      </ul>
      <div className="row">
        <Link href={`/schemes/${r.code}`}>{d.seeScheme}</Link>
        {r.status === "possible" && <button type="button" className="link" onClick={() => setStage("review")}>{d.editAnswers}</button>}
      </div>
      {r.status !== "excluded" && <Callback d={d} lang={lang} schemeCode={r.code} />}
    </article>
  );

  return (
    <section className="finder-panel" aria-live="polite">
      <div className="result-head" style={{ marginBottom: "0.5rem" }}>
        <h2 className="question" style={{ margin: 0 }}>{d.results}</h2>
        <div className="row">
          <button type="button" onClick={() => setStage("review")}>{d.editAnswers}</button>
          <button type="button" className="link" onClick={restart}>{d.startOver}</button>
        </div>
      </div>
      <p>{fill(d.resultsSummary, { match: match.length, possible: possible.length })}</p>
      <p className="muted">{d.disclaimer}</p>
      {match.length === 0 && possible.length === 0 && <p className="notice warn" style={{ marginTop: "1rem" }}>{d.noMatches}</p>}
      {match.length > 0 && <div className="section-gap"><h3>{d.groupMatch}</h3>{match.map(row)}</div>}
      {possible.length > 0 && <div className="section-gap"><h3>{d.groupPossible}</h3>{possible.map(row)}</div>}
      {excluded.length > 0 && (
        <details className="more section-gap">
          <summary>{fill(d.groupExcluded, { n: excluded.length })}</summary>
          {excluded.map(row)}
        </details>
      )}
      <div className="section-gap panel"><Callback d={d} lang={lang} open={match.length === 0 && possible.length === 0} /></div>
    </section>
  );
}

function selectValue(v: unknown): string {
  if (v === true) return "yes";
  if (v === false) return "no";
  return v === undefined ? "" : String(v);
}
