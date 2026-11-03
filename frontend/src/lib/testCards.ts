/** The published test cards shown on the payment page. The API decides the outcome. */
export const TEST_CARDS = [
  { number: "4242 4242 4242 4242", hi: "भुगतान सफल", en: "Payment succeeds" },
  { number: "4000 0000 0000 0002", hi: "बैंक मना कर देता है", en: "Bank declines" },
  { number: "4000 0000 0000 9995", hi: "खाते में राशि कम", en: "Not enough funds" },
  { number: "4000 0000 0000 0101", hi: "विदेशी कार्ड, रोका गया", en: "Foreign card, blocked" },
];
