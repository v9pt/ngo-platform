/** The finder's questions and the plain-language explanation of each rule. Pure, so it is
 * unit-tested and used by the browser without any server code. */

export type Lang = "hi" | "en";
export type Marital = "single" | "married" | "widow" | "divorced" | "separated";
export type Answers = {
  age?: number;
  marital_status?: Marital;
  district?: string;
  has_bpl_card?: boolean;
  pregnant?: boolean;
  first_child?: boolean;
  shg_member?: boolean;
  has_school_age_girl?: boolean;
  owns_pucca_house?: boolean;
};
export type AnswerKey = keyof Answers;
export type Rule = { field: string; op: string; value: unknown; outcome: "met" | "not_met" | "unknown" };

export const DISTRICTS = ["Bhopal", "Sehore", "Vidisha", "Raisen", "Rajgarh", "Indore", "Dewas", "Ujjain", "Narmadapuram"];
const DISTRICT_HI: Record<string, string> = {
  Bhopal: "भोपाल", Sehore: "सीहोर", Vidisha: "विदिशा", Raisen: "रायसेन", Rajgarh: "राजगढ़",
  Indore: "इंदौर", Dewas: "देवास", Ujjain: "उज्जैन", Narmadapuram: "नर्मदापुरम",
};
export const districtName = (name: string, lang: Lang) => (lang === "hi" && DISTRICT_HI[name]) || name;

export const MARITAL: { value: Marital; hi: string; en: string }[] = [
  { value: "single", hi: "अविवाहित", en: "Single" },
  { value: "married", hi: "विवाहित", en: "Married" },
  { value: "widow", hi: "विधवा", en: "Widow" },
  { value: "divorced", hi: "तलाकशुदा", en: "Divorced" },
  { value: "separated", hi: "अलग रह रही", en: "Separated" },
];

export const NEEDS = [
  { value: "pension", hi: "पेंशन", en: "Pension" },
  { value: "livelihood", hi: "रोज़गार और आजीविका", en: "Work and livelihood" },
  { value: "health", hi: "स्वास्थ्य और मातृत्व", en: "Health and maternity" },
  { value: "education", hi: "बेटी की पढ़ाई", en: "Girls' education" },
  { value: "housing", hi: "घर", en: "Housing" },
  { value: "safety", hi: "सुरक्षा और कानूनी मदद", en: "Safety and legal help" },
] as const;
export const needName = (value: string, lang: Lang) => NEEDS.find((n) => n.value === value)?.[lang] ?? value;

type Question = { key: AnswerKey; kind: "age" | "marital" | "district" | "yesno"; hi: string; en: string };
export const QUESTIONS: Question[] = [
  { key: "age", kind: "age", hi: "आपकी उम्र कितनी है?", en: "How old are you?" },
  { key: "marital_status", kind: "marital", hi: "आपकी वैवाहिक स्थिति क्या है?", en: "What is your marital status?" },
  { key: "district", kind: "district", hi: "आप किस ज़िले में रहती हैं?", en: "Which district do you live in?" },
  { key: "has_bpl_card", kind: "yesno", hi: "क्या आपके पास बीपीएल कार्ड है?", en: "Do you have a BPL card?" },
  { key: "pregnant", kind: "yesno", hi: "क्या आप गर्भवती हैं?", en: "Are you pregnant?" },
  { key: "first_child", kind: "yesno", hi: "क्या यह आपका पहला बच्चा है?", en: "Is this your first child?" },
  { key: "shg_member", kind: "yesno", hi: "क्या आप स्वयं सहायता समूह की सदस्य हैं?", en: "Are you in a self-help group?" },
  { key: "has_school_age_girl", kind: "yesno", hi: "क्या आपकी कोई बेटी स्कूल जाती है?", en: "Does a daughter of yours go to school?" },
  { key: "owns_pucca_house", kind: "yesno", hi: "क्या आपके पास पक्का मकान है?", en: "Do you own a pucca house?" },
];

/** A question that cannot apply is not asked: "first child" only follows "pregnant: yes". */
export function visibleQuestions(answers: Answers): Question[] {
  return QUESTIONS.filter((q) => q.key !== "first_child" || answers.pregnant === true);
}

/** What goes to the API. Blank answers are left out, which makes a rule "unknown", not false.
 * A first-child answer left over from before "pregnant" was changed is dropped too. */
export function toPayload(answers: Answers): Answers {
  const visible = new Set(visibleQuestions(answers).map((q) => q.key));
  return Object.fromEntries(
    Object.entries(answers).filter(([k, v]) => v !== undefined && v !== null && visible.has(k as AnswerKey)),
  ) as Answers;
}

/** Keeps only fields the form knows. The server's suggestions pass through here before use. */
export function fromSuggestion(raw: Record<string, unknown>): Answers {
  const keys = new Set<string>(QUESTIONS.map((q) => q.key));
  return Object.fromEntries(Object.entries(raw).filter(([k]) => keys.has(k))) as Answers;
}

export function ageError(value: string, lang: Lang): string | null {
  if (value.trim() === "") return null;
  const n = Number(value);
  if (Number.isInteger(n) && n >= 0 && n <= 120) return null;
  return lang === "hi" ? "उम्र 0 से 120 के बीच पूरी संख्या में लिखें।" : "Enter a whole number from 0 to 120.";
}

export function answerText(key: AnswerKey, answers: Answers, lang: Lang): string | null {
  const value = answers[key];
  if (value === undefined) return null;
  if (key === "marital_status") return MARITAL.find((m) => m.value === value)?.[lang] ?? null;
  if (key === "district") return districtName(String(value), lang);
  if (typeof value === "boolean") return value ? (lang === "hi" ? "हाँ" : "Yes") : (lang === "hi" ? "नहीं" : "No");
  return String(value);
}

const LABELS: Record<string, { yes: Record<Lang, string>; no: Record<Lang, string> }> = {
  has_bpl_card: { yes: { hi: "बीपीएल कार्ड हो", en: "Has a BPL card" }, no: { hi: "बीपीएल कार्ड न हो", en: "Does not have a BPL card" } },
  pregnant: { yes: { hi: "गर्भवती हों", en: "Is pregnant" }, no: { hi: "गर्भवती न हों", en: "Is not pregnant" } },
  first_child: { yes: { hi: "पहला बच्चा हो", en: "Expecting her first child" }, no: { hi: "पहला बच्चा न हो", en: "Not her first child" } },
  shg_member: { yes: { hi: "स्वयं सहायता समूह की सदस्य हों", en: "Is in a self-help group" }, no: { hi: "समूह की सदस्य न हों", en: "Is not in a self-help group" } },
  has_school_age_girl: { yes: { hi: "बेटी स्कूल जाती हो", en: "Has a daughter in school" }, no: { hi: "स्कूल जाने वाली बेटी न हो", en: "No daughter in school" } },
  owns_pucca_house: { yes: { hi: "पक्का मकान हो", en: "Owns a pucca house" }, no: { hi: "पक्का मकान न हो", en: "Does not own a pucca house" } },
};

/** The rule in words a person would use, never field names or operators. */
export function describeRule(rule: Pick<Rule, "field" | "op" | "value">, lang: Lang): string {
  const { field, op, value } = rule;
  if (field === "age" && op === "between" && Array.isArray(value)) {
    return lang === "hi" ? `उम्र ${value[0]} से ${value[1]} वर्ष के बीच हो` : `Aged ${value[0]} to ${value[1]}`;
  }
  if (field === "age" && op === "gte") {
    return lang === "hi" ? `उम्र ${String(value)} वर्ष या उससे अधिक हो` : `Aged ${String(value)} or above`;
  }
  if (field === "marital_status") {
    const items = (Array.isArray(value) ? value : [value]).map((v) => MARITAL.find((m) => m.value === v)?.[lang] ?? String(v));
    return lang === "hi" ? `स्थिति: ${items.join(" या ")}` : `Status: ${items.join(" or ")}`;
  }
  if (field === "district") {
    const items = (Array.isArray(value) ? value : [value]).map((v) => districtName(String(v), lang));
    return lang === "hi" ? `ज़िला: ${items.join(", ")}` : `District: ${items.join(", ")}`;
  }
  const label = LABELS[field];
  if (label) return (value === true ? label.yes : label.no)[lang];
  return field.replaceAll("_", " ");
}
