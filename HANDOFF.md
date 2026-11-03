# Handoff: NGO donation platform and women's schemes finder

Status as of 2026-11-03 (Day 5 of 7 done). Take-home brief #2. Delete this file before final submission.

## Decisions made
- Stack: Next.js (TypeScript) + FastAPI + Postgres. Managed Postgres, Docker host for the API, Vercel for the frontend.
- Donors **must have an account** to donate (no guest checkout).
- PAN encrypted at rest (Fernet, key from `PAN_ENCRYPTION_KEY`), masked in UI and logs.
- Light and dark mode with a System / Light / Dark toggle (default System). Hindi first.
- Money is integer paise. Financial year runs April to March. Receipts look like `RCPT/2026-27/000123`.
- Receipt number is assigned only on payment success, inside one transaction (design below).

## Done (all committed, 49 tests pass, ruff + mypy --strict clean)
- `backend/app/config.py`: env config validated at startup (fails fast).
- `backend/app/security.py`: argon2 passwords, HS256 session JWT (alg pinned, issuer checked), PAN validate/mask/encrypt.
- `backend/app/models.py` + Alembic migration `c5716c687fae`: users, schemes, scheme_summaries, campaigns, donations, receipt_counters, receipts, audit_log. DB-level invariants:
  - `receipts` is immutable (trigger blocks UPDATE/DELETE), `UNIQUE(fy, seq)`, `UNIQUE(donation_id)`.
  - donation minimum Rs 100, `UNIQUE(donor_id, idempotency_key)`, unique `gateway_ref`.
  - an approved summary must record approver and time.
- `backend/app/routers/auth.py`: register, login, logout, me. httpOnly SameSite=Lax cookie, role never taken from the client, generic login errors, constant-time-ish login, rate limits (per process).
- `backend/app/errors.py`: one RFC 7807 error shape; validation errors never echo values.
- `backend/app/seed.py`: idempotent seed (`python -m app.seed`). Demo accounts `admin@`, `editor@`, `donor@demo.example`, password `DemoPass#2026` (public demo credential), 7 illustrative schemes (rules as JSON), 3 campaigns, 1 approved + 1 AI-draft summary.
- Tests in `backend/tests/` run against a real Postgres and the real migration.

## Done on Day 2 (68 tests pass, ruff + mypy clean)
- `backend/app/receipts.py`: `issue_receipt` (donation row lock, then FY counter upsert, snapshot, mark paid). Concurrency + replay + April rollover tests in `tests/test_receipts.py`.
- `backend/app/routers/donations.py`: `POST /v1/donations` (Idempotency-Key required), `GET /v1/donations/{id}` (owner only, 404 otherwise), `POST /v1/webhooks/mock-gateway` (HMAC-SHA256 of raw body in `X-Signature`; needs new env `GATEWAY_WEBHOOK_SECRET`, 32+ chars).
- Local Postgres for tests: Homebrew `postgresql@15` binaries; use a short unix-socket dir (`-k /tmp/pgsock`).
- `GET /v1/donations` = donor history (done).

## Done on Day 3 (85 tests pass)
- `app/eligibility.py`: pure rule engine (`eq`, `in`, `between`, `gte`); per-rule met/not_met/unknown; excluded > possible > match; unknown operator raises.
- `app/routers/schemes.py`: `GET /v1/schemes[?need=]`, `GET /v1/schemes/{code}`, `POST /v1/schemes/check` (published only, best matches first, rules shown).
- PDF receipt `GET /v1/donations/{id}/receipt.pdf` (WeasyPrint; on macOS tests need `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`; Docker image needs pango).

## Done on Day 4 (frontend)
- `frontend/` now has: theme tokens (light/dark/system, cookie-driven, no flash), Hindi-first i18n dictionary + language toggle (`src/lib/i18n.ts`, server actions in `src/app/actions.ts`), home, `/schemes`, `/schemes/[code]`, `/finder` (client form -> `/api/v1/schemes/check`, shows per-rule reasons). `next.config.ts` rewrites `/api/*` to `API_URL` (same-origin, so session cookies work on Day 5). I removed `cacheComponents`/`partialPrefetching` from the create-next-app config: cookie-driven lang/theme needs dynamic rendering. `npm run lint` and `npm run build` pass; checked in the browser pane (Hindi, dark, widow profile gives 3 matches + 3 possible).
- Not yet: no frontend tests, no mobile/a11y audit (Day 6), scheme detail text fields beyond title/benefit are English only.

## Done on Day 5 (donation UI + donor account; 88 backend tests)
- Backend: `GET /v1/campaigns` (live only, `raised_paise` from paid donations).
- Frontend: `/register`, `/login`, `/account` (history, receipt PDF links, log out), `/donate` (campaigns + progress + form with a per-mount Idempotency-Key), `/donate/pay/[id]` (test-mode "gateway": server action signs the webhook with `GATEWAY_WEBHOOK_SECRET`, owner-checked, refuses if `GATEWAY_MODE=live`). Header shows Donate and Account/Login.
- Verified in the browser: register -> donate Rs 500 -> simulate payment -> receipt RCPT/2026-27/000001 -> PDF 200 via proxy.
- Gaps: PAN capture for 80G is not in the UI yet (receipt shows "Not provided"); monthly is a stored kind only (assumption A7, no scheduler yet); no frontend tests; Hindi-first strings for new pages are in but only skimmed.

## Not done yet
- No scheme/eligibility endpoints, donation flow, receipt issuing, PDF, CMS, AI summaries, CI, README, Dockerfile, deployment.md, TDD.
- No GitHub remote yet. Repo must be public with the URL at the top of the TDD.

## Run it locally
```bash
# Postgres 16 on port 5433 with a database `ngo_test` (any Postgres works; set TEST_DATABASE_URL)
cd backend
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
export DATABASE_URL='postgresql+psycopg://postgres@localhost:5433/ngo_test'
alembic upgrade head
python -m app.seed
python -m pytest -q          # 49 passed
ruff check . && ruff format --check . && mypy app
```
To run the API you also need `JWT_SECRET` (32+ chars) and `PAN_ENCRYPTION_KEY` (see `.env.example`), then `uvicorn app.main:create_app --factory --reload`.

## Design to implement next (the riskiest part: do it before UI)
Receipt issue transaction, in this lock order:
```sql
BEGIN;
SELECT ... FROM donations WHERE gateway_ref = :ref FOR UPDATE;  -- if already 'paid', return existing receipt
UPDATE receipt_counters SET last_seq = last_seq + 1 WHERE fy = :fy RETURNING last_seq;
INSERT INTO receipts (...snapshot of donor name/email/PAN ciphertext/amount/campaign/trust...);
UPDATE donations SET status='paid', paid_at=now() WHERE id=:id;
COMMIT;
```
- Counter row for the FY must exist (seed creates it; also upsert on first use of a new FY).
- Verify the mock gateway webhook with an HMAC signature, fail closed.
- Render the PDF from the receipt snapshot with WeasyPrint in a worker thread with a concurrency cap (never on the event loop). Verify WeasyPrint's system packages in the Docker image.
- Concurrency test: 200 parallel payments, assert no duplicate seq and no gaps; replayed webhook returns the same receipt.

Other planned pieces: eligibility engine (rule ops used in seed: `eq`, `in`, `between`, `gte`; fields: `age`, `marital_status`, `has_bpl_card`, `pregnant`, `first_child`, `shg_member`, `has_school_age_girl`, `owns_pucca_house`, `district`; results are match / possible / excluded with rules shown); AI Hindi summary drafts (fence the notice as data, deterministic checks: mostly Devanagari, length bound, every number in the summary appears in the source, editor must approve); admin CMS with draft -> in_review -> published; campaign report + 10BD-style CSV; donor account with history.

## Schedule (remaining)
Day 2 receipt txn + concurrency test + donation API + mock gateway; Day 3 schemes API + eligibility engine + tests; Day 4 frontend (home, finder, scheme pages, theme tokens); Day 5 donation flow UI + PDF + donor account; Day 6 CMS + AI summaries + a11y/mobile pass; Day 7 CI, deploy, deployment.md, TDD, final QA.

## Assumptions to label in the TDD
A1 sample data illustrative; A2 nine MP districts invented (brief names none); A3 trust PAN / 80G number are fake placeholders; A4 PAN required for an 80G certificate; A5 10BD export is a CSV with common columns, not the official utility format; A6 "foreign card blocked" simulated with a test-card country field; A7 monthly giving is a test-mode mandate with a mock scheduler; A8 rate limiting is per process.

## Docs
Claude Doc with the plan: https://claude.ai/artifact/Gu3xBMPKVLEW579bGp6M6p
