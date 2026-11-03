import type { Dict } from "@/lib/i18n";

export function DonateSteps({ d, current }: { d: Dict; current: 1 | 2 | 3 }) {
  const steps = [d.stepGift, d.stepPay, d.stepReceipt];
  return (
    <ol className="steps">
      {steps.map((label, i) => (
        <li key={label} aria-current={current === i + 1 ? "step" : undefined}><b>{i + 1}</b>{label}</li>
      ))}
    </ol>
  );
}
