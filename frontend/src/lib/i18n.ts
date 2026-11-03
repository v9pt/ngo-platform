import { cookies } from "next/headers";

export type Lang = "hi" | "en";
export type Theme = "system" | "light" | "dark";

export async function getLang(): Promise<Lang> {
  const v = (await cookies()).get("lang")?.value;
  return v === "en" ? "en" : "hi"; // Hindi first
}

export async function getTheme(): Promise<Theme> {
  const v = (await cookies()).get("theme")?.value;
  return v === "light" || v === "dark" ? v : "system";
}

const hi = {
    siteName: "महिला विकास ट्रस्ट",
    home: "मुख्य पृष्ठ",
    schemes: "योजनाएँ",
    finder: "योजना खोजें",
    donate: "दान करें",
    language: "भाषा",
    theme: "थीम",
    themeSystem: "सिस्टम",
    themeLight: "हल्का",
    themeDark: "गहरा",
    heroTitle: "आपके लिए सही सरकारी योजना खोजें",
    heroText:
      "कुछ सरल सवालों के जवाब दें। हम बताएँगे कि कौन-सी योजना आपके लिए उपयुक्त हो सकती है, और क्यों।",
    startFinder: "योजना खोजना शुरू करें",
    browseSchemes: "सभी योजनाएँ देखें",
    sampleNote: "इस डेमो में दी गई योजनाओं की जानकारी उदाहरण के लिए है। आवेदन से पहले आधिकारिक स्रोत देखें।",
    benefit: "लाभ",
    whoCanApply: "कौन आवेदन कर सकता है",
    documents: "ज़रूरी दस्तावेज़",
    howToApply: "आवेदन कैसे करें",
    helpCentre: "सहायता केंद्र",
    source: "आधिकारिक स्रोत",
    lastChecked: "अंतिम जाँच",
    needAll: "सभी ज़रूरतें",
    age: "आपकी उम्र",
    maritalStatus: "वैवाहिक स्थिति",
    district: "ज़िला",
    notSure: "बताना नहीं चाहते / पता नहीं",
    yes: "हाँ",
    no: "नहीं",
    check: "योजनाएँ जाँचें",
    results: "आपके नतीजे",
    match: "उपयुक्त",
    possible: "संभव",
    excluded: "उपयुक्त नहीं",
    met: "पूरा",
    not_met: "पूरा नहीं",
    unknown: "जवाब नहीं दिया",
    loadError: "जानकारी अभी नहीं मिल सकी। कृपया थोड़ी देर बाद कोशिश करें।",
    noSchemes: "कोई योजना नहीं मिली।",
    back: "वापस",
    q_has_bpl_card: "क्या आपके पास बीपीएल राशन कार्ड है?",
    q_pregnant: "क्या आप गर्भवती हैं?",
    q_first_child: "क्या यह आपका पहला बच्चा है?",
    q_shg_member: "क्या आप स्वयं सहायता समूह की सदस्य हैं?",
    q_has_school_age_girl: "क्या आपके परिवार में स्कूल जाने की उम्र की बेटी है?",
    q_owns_pucca_house: "क्या आपके पास पक्का मकान है?",
    marital_single: "अविवाहित",
    marital_married: "विवाहित",
    marital_widow: "विधवा",
    marital_divorced: "तलाकशुदा",
    marital_separated: "अलग रह रही",
} as const;

export type Dict = Record<keyof typeof hi, string>;

const en: Dict = {
    siteName: "Mahila Vikas Trust",
    home: "Home",
    schemes: "Schemes",
    finder: "Find a scheme",
    donate: "Donate",
    language: "Language",
    theme: "Theme",
    themeSystem: "System",
    themeLight: "Light",
    themeDark: "Dark",
    heroTitle: "Find the government scheme that fits you",
    heroText:
      "Answer a few simple questions. We show which schemes may suit you, and exactly why.",
    startFinder: "Start the scheme finder",
    browseSchemes: "Browse all schemes",
    sampleNote: "Scheme details in this demo are illustrative. Check the official source before applying.",
    benefit: "Benefit",
    whoCanApply: "Who can apply",
    documents: "Documents needed",
    howToApply: "How to apply",
    helpCentre: "Help centre",
    source: "Official source",
    lastChecked: "Last checked",
    needAll: "All needs",
    age: "Your age",
    maritalStatus: "Marital status",
    district: "District",
    notSure: "Prefer not to say / not sure",
    yes: "Yes",
    no: "No",
    check: "Check schemes",
    results: "Your results",
    match: "Likely eligible",
    possible: "Possibly eligible",
    excluded: "Not eligible",
    met: "Met",
    not_met: "Not met",
    unknown: "Not answered",
    loadError: "We could not load this right now. Please try again shortly.",
    noSchemes: "No schemes found.",
    back: "Back",
    q_has_bpl_card: "Do you have a BPL ration card?",
    q_pregnant: "Are you pregnant?",
    q_first_child: "Is this your first child?",
    q_shg_member: "Are you a member of a self-help group?",
    q_has_school_age_girl: "Is there a school-age girl in your family?",
    q_owns_pucca_house: "Do you own a pucca house?",
    marital_single: "Single",
    marital_married: "Married",
    marital_widow: "Widow",
    marital_divorced: "Divorced",
    marital_separated: "Separated",
};

const dict: { hi: Dict; en: Dict } = { hi, en };
export function t(lang: Lang): Dict {
  return dict[lang];
}
