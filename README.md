# Mahila Vikas Trust: schemes finder and donations

Last updated: 2026-11-03 12:20 PM CST

[![CI](https://github.com/v9pt/ngo-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/v9pt/ngo-platform/actions/workflows/ci.yml)

A Hindi-first site for a Bhopal women's livelihoods trust. A woman finds the government schemes she
may qualify for, and why. A donor gives to a campaign and gets a numbered receipt and 80G certificate
the moment payment succeeds. Editors and admins maintain schemes with review before publishing.

Design and decisions: [docs/TDD.pdf](docs/TDD.pdf). Running and deploying: [deployment.md](deployment.md).

## Stack
Next.js 16 (TypeScript), FastAPI with SQLAlchemy, PostgreSQL, Alembic, WeasyPrint for PDFs, Claude for
AI features.

## What works
- **Finder:** type your situation in Hindi or answer one question at a time. You see and can change
  every answer. Rules decide, and each result says why in plain words, with a helpline call-back.
- **Donations:** campaign, amount, PAN, test-card payment, instant receipt PDF. Declines and foreign
  cards explain themselves and can be retried. Monthly giving can be stopped from the account.
- **Staff:** create and edit schemes and rules, review before publishing, AI or hand-written Hindi
  summaries that are checked before approval, a call-back queue, reports and a masked CSV export.
- **Quality:** Hindi and English, light, dark and device themes, phone layouts, and designed loading,
  empty and error states.

## Run it
Step-by-step instructions, demo logins and test cards are in [deployment.md](deployment.md).

## Checks
```bash
cd backend && ruff check . && ruff format --check . && mypy app tests && python -m pytest -q
```

```bash
cd frontend && npm run lint && npx tsc --noEmit && npm test && npm run build && npm run test:e2e
```

Backend tests run against a real Postgres built by the real migrations (set `TEST_DATABASE_URL`).
Browser tests need the API and site running. CI runs all of this (`.github/workflows/ci.yml`).
`backend/scripts/load_receipts.py` measures receipt issuing; run it on a throwaway database only.

## Troubleshooting
| Problem | Fix |
|---|---|
| Receipt PDF gives a 500 on macOS | `brew install pango`, then start the API with `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` |
| Campaigns show ₹0 and the report is empty | Run the seed with `PAN_ENCRYPTION_KEY` set; without it only the catalogue is seeded |
| "AI drafting is not configured" | Expected with no `ANTHROPIC_API_KEY`. Write the summary by hand, or set the key |
| Pages show "could not load" | The API is not reachable at `API_URL`; check `curl $API_URL/ready` |

## Known limits
Sample schemes, the payment gateway, the trust's details and the 10BD format are placeholders. The
full list of assumptions and gaps is in the TDD.
