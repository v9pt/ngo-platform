import { appendSpoken } from "./voice";
import { describe, expect, it } from "vitest";
import { ageError, answerText, describeRule, fromSuggestion, toPayload, visibleQuestions } from "./finder";
import { fill, isStale, rupees, safeNext } from "./format";

describe("visibleQuestions", () => {
  const keys = (a: object) => visibleQuestions(a).map((q) => q.key);
  it("asks about a first child only after a yes to pregnant", () => {
    expect(keys({})).not.toContain("first_child");
    expect(keys({ pregnant: false })).not.toContain("first_child");
    expect(keys({ pregnant: true })).toContain("first_child");
  });
});

describe("toPayload", () => {
  it("leaves blanks out, so a rule becomes unknown and not false", () => {
    expect(toPayload({ age: 40, district: undefined })).toEqual({ age: 40 });
  });
  it("keeps a real no, because false is an answer", () => {
    expect(toPayload({ has_bpl_card: false })).toEqual({ has_bpl_card: false });
  });
  it("drops a stale first-child answer once pregnant changes to no", () => {
    expect(toPayload({ pregnant: false, first_child: true })).toEqual({ pregnant: false });
  });
});

describe("fromSuggestion", () => {
  it("ignores fields the form does not know", () => {
    expect(fromSuggestion({ age: 30, income: 5000 })).toEqual({ age: 30 });
  });
});

describe("ageError", () => {
  it("accepts blank and whole ages in range", () => {
    for (const v of ["", " ", "0", "45", "120"]) expect(ageError(v, "en")).toBeNull();
  });
  it("refuses anything else", () => {
    for (const v of ["-1", "121", "4.5", "abc"]) expect(ageError(v, "en")).not.toBeNull();
  });
});

describe("answerText", () => {
  it("shows answers in the visitor's language", () => {
    expect(answerText("marital_status", { marital_status: "widow" }, "hi")).toBe("विधवा");
    expect(answerText("has_bpl_card", { has_bpl_card: false }, "en")).toBe("No");
    expect(answerText("district", { district: "Bhopal" }, "hi")).toBe("भोपाल");
    expect(answerText("age", {}, "en")).toBeNull();
  });
});

describe("describeRule", () => {
  it("never shows field names or operators to a woman using the finder", () => {
    const rules = [
      { field: "age", op: "between", value: [18, 79] }, { field: "age", op: "gte", value: 30 },
      { field: "marital_status", op: "eq", value: "widow" }, { field: "district", op: "in", value: ["Bhopal", "Raisen"] },
      { field: "has_bpl_card", op: "eq", value: true }, { field: "owns_pucca_house", op: "eq", value: false },
    ];
    for (const lang of ["hi", "en"] as const) {
      for (const r of rules) {
        const text = describeRule(r, lang);
        expect(text).not.toMatch(/_|between|gte|\[|\]|"/);
        expect(text.length).toBeGreaterThan(3);
      }
    }
  });
  it("words each rule correctly", () => {
    expect(describeRule({ field: "age", op: "between", value: [18, 79] }, "hi")).toBe("उम्र 18 से 79 वर्ष के बीच हो");
    expect(describeRule({ field: "owns_pucca_house", op: "eq", value: false }, "en")).toBe("Does not own a pucca house");
    expect(describeRule({ field: "district", op: "in", value: ["Bhopal", "Raisen"] }, "hi")).toBe("ज़िला: भोपाल, रायसेन");
  });
});

describe("format", () => {
  it("groups rupees the Indian way and shows paise only when present", () => {
    expect(rupees(12345600)).toBe("₹1,23,456");
    expect(rupees(10050)).toBe("₹100.50");
  });
  it("safeNext allows only paths on this site", () => {
    expect(safeNext("/donate")).toBe("/donate");
    for (const bad of ["https://evil.example", "//evil.example", "/\\evil.example", "donate", "", null, undefined]) {
      expect(safeNext(bad)).toBeNull();
    }
  });
  it("isStale flags facts not checked for about six months", () => {
    const now = new Date("2026-11-03");
    expect(isStale("2026-10-01", now)).toBe(false);
    expect(isStale("2026-03-01", now)).toBe(true);
  });
  it("fill replaces every placeholder", () => {
    expect(fill("{n} of {n} for {who}", { n: 2, who: "Asha" })).toBe("2 of 2 for Asha");
  });
});

describe("appendSpoken", () => {
  it("adds speech after typed text", () => expect(appendSpoken("मैं विधवा हूँ", "भोपाल में")).toBe("मैं विधवा हूँ भोपाल में"));
  it("ignores empty speech", () => expect(appendSpoken("abc", "  ")).toBe("abc"));
  it("respects the length cap", () => expect(appendSpoken("a".repeat(498), "bcdef", 500)).toHaveLength(500));
});
