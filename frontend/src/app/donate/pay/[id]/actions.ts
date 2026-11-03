"use server";

import { createHmac } from "node:crypto";
import { redirect } from "next/navigation";
import { authedFetch } from "@/lib/api";

const API = process.env.API_URL ?? "http://localhost:8000";

/**
 * Test-mode stand-in for the payment gateway calling our webhook. The secret never leaves the
 * server. Only the signed-in owner of the donation may trigger it (checked against the API),
 * and it is disabled outside test mode.
 */
export async function simulatePayment(formData: FormData) {
  if (process.env.GATEWAY_MODE === "live") throw new Error("Mock gateway is disabled");
  const secret = process.env.GATEWAY_WEBHOOK_SECRET;
  if (!secret) throw new Error("GATEWAY_WEBHOOK_SECRET is not set");
  const donationId = String(formData.get("donation_id"));
  const owned = await authedFetch(`/v1/donations/${encodeURIComponent(donationId)}`);
  if (!owned.ok) throw new Error("Donation not found");
  const gatewayRef = ((await owned.json()) as { gateway_ref: string }).gateway_ref;
  const event = formData.get("event") === "payment.failed" ? "payment.failed" : "payment.succeeded";
  const body = JSON.stringify({ gateway_ref: gatewayRef, event });
  const signature = createHmac("sha256", secret).update(body).digest("hex");
  const r = await fetch(`${API}/v1/webhooks/mock-gateway`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Signature": signature },
    body,
  });
  if (!r.ok) throw new Error("Payment could not be recorded");
  redirect(`/donate/pay/${donationId}`);
}
