# Deployment

**Live app:** not deployed yet. This file gives the exact path; everything under "Run it locally" was
run from a clean database.

## Demo logins for the reviewer
The password for all three is `DemoPass#2026`. It is a public demo credential, used nowhere else. The
login page also has buttons that fill these in.

| Role | Email | Can do |
|---|---|---|
| Donor | `donor@demo.example` | Donate, see receipts, change PAN, stop monthly giving |
| Editor | `editor@demo.example` | Edit schemes and rules, send for review, write and approve summaries, work the call-back queue |
| Trust admin | `admin@demo.example` | All of the above, plus publish, reports, CSV export, monthly charge run |

## Test cards
Only these numbers are accepted, so nobody can type a real card into the demo.

| Card | Result |
|---|---|
| `4242 4242 4242 4242` | Payment succeeds |
| `4000 0000 0000 0002` | Bank declines |
| `4000 0000 0000 9995` | Not enough funds |
| `4000 0000 0000 0101` | Foreign card, blocked. Choosing another issuing country blocks any card |

## Run it locally
You need Python 3.11 or 3.12, Node 22 or later, PostgreSQL 15 or later, and pango for PDFs
(`brew install pango` on macOS). Replace the database URL if yours differs.

### 1. API
```bash
cd backend
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
createdb ngo
export DATABASE_URL='postgresql+psycopg://postgres@localhost:5432/ngo'
export JWT_SECRET="$(python -c 'import secrets;print(secrets.token_urlsafe(48))')"
export GATEWAY_WEBHOOK_SECRET="$(python -c 'import secrets;print(secrets.token_urlsafe(48))')"
export PAN_ENCRYPTION_KEY="$(python -c 'from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())')"
export DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib   # macOS only, for PDF rendering
alembic upgrade head
python -m app.seed
uvicorn app.main:create_app --factory --port 8000
```
Run the seed with `PAN_ENCRYPTION_KEY` set, as above, or the sample giving history is skipped. Keep the
same key between runs: stored PANs cannot be read with a different one.

### 2. Site, in a second terminal
```bash
cd frontend
npm ci
npm run dev
```
Open http://localhost:3000. It is in Hindi first; the English button is in the header.

### 3. Optional: turn on AI
```bash
export ANTHROPIC_API_KEY=your-key-here
```
Set it before starting the API. Without it the app still works: the finder uses its keyword reader,
and editors write summaries by hand.

## How it is deployed
Vercel (site) -> Docker host (API) -> managed PostgreSQL. The browser only talks to the site. A rewrite
sends `/api/*` to the API, so the session cookie stays same-origin.

### Database
Create a managed PostgreSQL database and a user for the app. Use the driver prefix
`postgresql+psycopg://`. Turn on automated backups and test one restore.

### API
```bash
docker build -t ngo-api backend
```
Run once per deploy, **before** starting the new containers:
```bash
docker run --rm --env-file prod.env ngo-api alembic upgrade head
docker run --rm --env-file prod.env ngo-api python -m app.seed
```
The seed is for demo data; skip it in a real deployment. Run the API behind TLS. `/health` is liveness
and does not touch the database. `/ready` checks the database.

### Site
Vercel project root `frontend/`, with `API_URL` set before the build, because the rewrite is fixed at
build time.

### Environment variables (names only)
| Variable | Where | Notes |
|---|---|---|
| `APP_ENV` | API | `prod` requires `CORS_ORIGINS` and makes cookies Secure |
| `DATABASE_URL` | API | `postgresql+psycopg://...` |
| `JWT_SECRET` | API | 32 or more random characters |
| `PAN_ENCRYPTION_KEY` | API | Fernet key. Losing it makes stored PANs unreadable, so back it up separately |
| `GATEWAY_WEBHOOK_SECRET` | API | 32 or more characters. Signs gateway webhooks |
| `CORS_ORIGINS` | API | The site's origin, comma separated, never `*` |
| `GATEWAY_MODE` | API | `test` (default) or `live`. `live` turns off the card simulator and monthly run |
| `TRUST_NAME`, `TRUST_PAN`, `TRUST_80G_REG` | API | Printed on receipts. Placeholders if unset |
| `SEED_DEMO_PASSWORD` | API, seed only | Optional. Overrides the demo password |
| `ANTHROPIC_API_KEY`, `SUMMARY_MODEL` | API | Optional. Give this app its own key |
| `FORWARDED_ALLOW_IPS` | API | The proxy's address. Without it every visitor shares one rate limit |
| `API_URL` | Site | Public HTTPS URL of the API |
| `SHOW_DEMO_LOGINS` | Site | `false` hides the demo accounts panel |

### After deploying
- `GET <api>/ready` returns `{"status":"ready"}`.
- Log in as the donor, donate with `4242 4242 4242 4242`, and download the receipt PDF.
- Change the demo passwords, or do not seed, for anything beyond a demo.

### Rollback
Redeploy the previous image. Take a database backup before any release with a migration: migrations
run forward in normal operation, and restoring the backup is the tested way back.
