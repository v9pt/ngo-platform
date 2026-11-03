# Technical design document

Repository: https://github.com/v9pt/ngo-platform

## 1. Goal and scope
A donation platform for a women's-welfare trust, plus a finder that tells a woman which government
schemes she may qualify for and why. Donors must have an account (receipts and 80G need an
identity). Editors maintain scheme content; admins publish it.

Out of scope: a real payment gateway, real recurring billing, the official 10BD utility format,
SMS/email delivery, Hindi for staff screens.

## 2. Architecture
Vercel (Next.js) -> `/api/*` rewrite -> FastAPI -> Postgres. The browser only talks to the
frontend origin, so the httpOnly SameSite=Lax session cookie works without CORS. The frontend
server calls the API directly for server-rendered pages and forwards the visitor's cookie.

Money is integer paise everywhere. Financial year runs April to March (`2026-27`).

## 3. The riskiest part: receipts
Requirement: gapless, unique, per-financial-year numbers (`RCPT/2026-27/000123`) issued exactly
once per paid donation, even when the gateway retries or many payments land at once.

One transaction, fixed lock order:
1. lock the donation row (`FOR UPDATE`); if a receipt exists, return it (replay-safe);
2. upsert the FY counter row (`INSERT ... ON CONFLICT DO UPDATE SET last_seq = last_seq + 1
   RETURNING`), which locks it until commit, so a rollback never burns a number;
3. insert the receipt with a snapshot of donor name, email, PAN ciphertext, amount, campaign
   title and trust details; mark the donation paid.

The database enforces the invariants too: `UNIQUE(fy, seq)`, `UNIQUE(donation_id)`, a trigger that
blocks UPDATE/DELETE on receipts, a Rs 100 minimum, `UNIQUE(donor_id, idempotency_key)`.
PDFs render from the snapshot, so a re-download is identical forever.

Evidence: `tests/test_receipts.py` runs 200 payments, each delivered twice concurrently, and
asserts sequence 1..200 with no gaps or duplicates. Replacing the counter with `MAX(seq)+1` makes
that test fail, which confirms it can catch the bug.

## 4. Payments
The mock gateway signs `{gateway_ref, event}` with HMAC-SHA256; the webhook verifies the raw body
before parsing and fails closed. A `payment.failed` event never downgrades a paid donation. The
test-mode "simulate payment" server action holds the secret server-side, checks the donor owns the
donation, and refuses when `GATEWAY_MODE=live`.

## 5. Eligibility
Rules are data (`field`, `op`, `value`; ops `eq`, `in`, `between`, `gte`) evaluated by a pure
function. Each rule is met / not met / unknown. Any not-met excludes; unknowns without failures
give "possible"; all met gives "match". The API returns every rule so the UI explains the result.
Unknown operators raise instead of silently passing.

## 6. Content workflow and AI summaries
Schemes: draft -> in_review (editor or admin) -> published (admin only); published schemes are
immutable until unpublished; every transition is audit-logged.

Hindi summaries drafted by Claude are only drafts. The notice is fenced as data in the prompt.
Deterministic checks run on the output and again on edit and approval: mostly Devanagari, 40-600
characters, and every number must appear in the source notice (handles Devanagari digits and
lakh). A flagged draft cannot be approved. Only the latest approved summary is public.
The live Anthropic call is untested in this build (no key); tests use a stub generator.

## 7. Security
argon2 passwords; HS256 session JWT with pinned algorithm and issuer; role always read from the
database; generic login errors with constant-time-ish verification; per-process rate limits (A8);
PAN validated, Fernet-encrypted at rest, masked everywhere it is displayed or exported; RFC 7807
errors that never echo submitted values; strict request models (unknown fields rejected);
owner-only donation access returns 404 not 403; CSV export neutralises formula injection;
config validated at startup so a bad deployment refuses to boot.

## 8. Testing
113 backend tests against a real Postgres built by the real migration: schema invariants,
auth, config, security helpers, seed idempotence, receipts (concurrency, replay, April rollover),
donations and webhook signatures, PDF, schemes and eligibility, campaigns, CMS workflow and
summary checks, report and CSV. ruff and mypy --strict run clean. The frontend has lint, type
check and build only; no component or end-to-end tests. UI flows were checked by hand in a browser.

## 9. Assumptions
- A1 Sample scheme data is illustrative.
- A2 The nine Madhya Pradesh districts are invented (the brief names none).
- A3 Trust PAN and 80G number are fake placeholders.
- A4 A PAN is required for an 80G certificate. (The UI has no PAN entry yet.)
- A5 The 10BD export is a CSV with common columns and masked PAN, not the official format.
- A6 "Foreign card blocked" is out of scope in this build.
- A7 Monthly giving is stored as a donation kind; there is no mandate or scheduler.
- A8 Rate limiting is per process.

## 10. Known gaps and next steps
PAN capture UI and certificate; monthly scheduler; real gateway; friendly errors for failed
editor actions; staff UI in Hindi; automated accessibility and end-to-end tests; shared rate
limiter; Docker image build and CI not yet run on a real remote.
