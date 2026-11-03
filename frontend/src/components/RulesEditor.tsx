"use client";

import { useState } from "react";
import type { EditableRule } from "@/lib/api";
import { DISTRICTS, MARITAL, describeRule } from "@/lib/finder";

type Row = { key: number; field: string; low: string; high: string; choice: string; list: string[] };

const FIELDS: [string, string][] = [
  ["age", "Age"], ["marital_status", "Marital status"], ["district", "District"],
  ["has_bpl_card", "Has a BPL card"], ["pregnant", "Pregnant"], ["first_child", "First child"],
  ["shg_member", "In a self-help group"], ["has_school_age_girl", "Daughter in school"], ["owns_pucca_house", "Owns a pucca house"],
];

function toRow(rule: EditableRule, key: number): Row {
  const row: Row = { key, field: rule.field, low: "", high: "", choice: "yes", list: [] };
  if (rule.field === "age") {
    if (Array.isArray(rule.value)) { row.low = String(rule.value[0]); row.high = String(rule.value[1]); }
    else row.low = String(rule.value);
  } else if (rule.field === "marital_status" || rule.field === "district") {
    row.list = (Array.isArray(rule.value) ? rule.value : [rule.value]).map(String);
  } else {
    row.choice = rule.value === false ? "no" : "yes";
  }
  return row;
}

export function toRule(row: Row): EditableRule | null {
  if (row.field === "age") {
    if (row.low === "") return null;
    return row.high === ""
      ? { field: "age", op: "gte", value: Number(row.low) }
      : { field: "age", op: "between", value: [Number(row.low), Number(row.high)] };
  }
  if (row.field === "marital_status" || row.field === "district") {
    return row.list.length ? { field: row.field, op: "in", value: row.list } : null;
  }
  return { field: row.field, op: "eq", value: row.choice === "yes" };
}

/** Editors build rules from plain fields. The hidden input carries them as JSON to the API,
 * which validates each one again before saving. */
export function RulesEditor({ initial, disabled }: { initial: EditableRule[]; disabled: boolean }) {
  const [rows, setRows] = useState<Row[]>(() => initial.map(toRow));
  const [nextKey, setNextKey] = useState(initial.length);
  const update = (key: number, patch: Partial<Row>) =>
    setRows((rs) => rs.map((r) => (r.key === key ? { ...r, ...patch } : r)));
  const rules = rows.map(toRule).filter((r): r is EditableRule => r !== null);

  return (
    <div className="stack">
      <input type="hidden" name="rules" value={JSON.stringify(rules)} />
      {rows.length === 0 && <p className="notice warn">No rules yet. A scheme needs at least one before it can be published.</p>}
      {rows.map((row) => {
        const rule = toRule(row);
        return (
          <div key={row.key} className="rule-row">
            <div className="field">
              <label htmlFor={`f-${row.key}`}>Question</label>
              <select id={`f-${row.key}`} value={row.field} disabled={disabled}
                      onChange={(e) => update(row.key, { field: e.target.value, low: "", high: "", list: [], choice: "yes" })}>
                {FIELDS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </div>
            {row.field === "age" ? (
              <>
                <div className="field"><label htmlFor={`lo-${row.key}`}>Minimum age</label>
                  <input id={`lo-${row.key}`} type="number" min={0} max={120} disabled={disabled} value={row.low} onChange={(e) => update(row.key, { low: e.target.value })} /></div>
                <div className="field"><label htmlFor={`hi-${row.key}`}>Maximum age (optional)</label>
                  <input id={`hi-${row.key}`} type="number" min={0} max={120} disabled={disabled} value={row.high} onChange={(e) => update(row.key, { high: e.target.value })} /></div>
              </>
            ) : row.field === "marital_status" || row.field === "district" ? (
              <fieldset className="field" style={{ gridColumn: "span 2" }}>
                <legend>Any of</legend>
                <div className="row">
                  {(row.field === "district" ? DISTRICTS.map((x) => [x, x]) : MARITAL.map((m) => [m.value, m.en])).map(([value, label]) => (
                    <label key={value} className="check" style={{ minHeight: "auto" }}>
                      <input type="checkbox" disabled={disabled} checked={row.list.includes(value)}
                             onChange={(e) => update(row.key, { list: e.target.checked ? [...row.list, value] : row.list.filter((x) => x !== value) })} />
                      {label}
                    </label>
                  ))}
                </div>
              </fieldset>
            ) : (
              <div className="field" style={{ gridColumn: "span 2" }}><label htmlFor={`c-${row.key}`}>Required answer</label>
                <select id={`c-${row.key}`} disabled={disabled} value={row.choice} onChange={(e) => update(row.key, { choice: e.target.value })}>
                  <option value="yes">Yes</option><option value="no">No</option>
                </select></div>
            )}
            <button type="button" disabled={disabled} onClick={() => setRows((rs) => rs.filter((r) => r.key !== row.key))}>Remove</button>
            <p className="muted" style={{ gridColumn: "1 / -1" }}>
              {rule ? <>Shown to women as: <span lang="hi">{describeRule(rule, "hi")}</span></> : "Incomplete: this rule will not be saved."}
            </p>
          </div>
        );
      })}
      <button type="button" disabled={disabled} onClick={() => {
        setRows((rs) => [...rs, { key: nextKey, field: "age", low: "", high: "", choice: "yes", list: [] }]);
        setNextKey((k) => k + 1);
      }}>Add a rule</button>
    </div>
  );
}
