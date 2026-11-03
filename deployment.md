# Deployment

Topology: Vercel (frontend) -> Docker host (API) -> managed Postgres 16. Nothing here has been
deployed from this repository yet; the steps are the intended path and the commands are tested
locally except where marked.

## 1. Database
Create a managed Postgres 16 database and a user for the app. Note the connection string and use
the driver prefix `postgresql+psycopg://`. Turn on automated backups and test one restore.

## 2. API (Docker host)
Build and run the image from `backend/`:

```bash
docker build -t ngo-api backend
```

Environment (names only; generate secrets, never commit them):

| Variable | Notes |
|---|---|
| `APP_ENV` | `prod` (requires `CORS_ORIGINS`, secure cookies) |
| `DATABASE_URL` | `postgresql+psycopg://...` |
| `JWT_SECRET` | 32+ random characters |
| `PAN_ENCRYPTION_KEY` | Fernet key. Losing it makes stored PANs unreadable; back it up separately |
| `GATEWAY_WEBHOOK_SECRET` | 32+ characters, shared with the frontend server |
| `CORS_ORIGINS` | the Vercel origin(s), comma separated, no `*` |
| `TRUST_NAME`, `TRUST_PAN`, `TRUST_80G_REG` | receipt details (placeholders in this demo) |
| `ANTHROPIC_API_KEY`, `SUMMARY_MODEL` | optional; without a key AI drafting answers 503 |

Release step, run once per deploy **before** starting the new containers:

```bash
docker run --rm --env-file prod.env ngo-api alembic upgrade head
docker run --rm --env-file prod.env ngo-api python -m app.seed   # demo data only; skip in a real deployment
```

Run the API behind TLS (reverse proxy or the host's load balancer). `/health` is liveness and
does not touch the database; `/ready` checks the database. Rate limits are per process (A8): with
more than one instance, put a shared limiter at the proxy.

## 3. Frontend (Vercel)
Project root `frontend/`. Environment: `API_URL` (public HTTPS URL of the API) and
`GATEWAY_WEBHOOK_SECRET` (same value as the API). The `/api/*` rewrite proxies browser calls to
the API so the session cookie stays same-origin. Set `GATEWAY_MODE=live` only when a real gateway
replaces the test-mode payment simulation; it disables the simulation action.

## 4. After deploy
- `GET <api>/ready` returns `{"status":"ready"}`.
- Register, donate with the test-mode payment, download the receipt PDF.
- Change the seeded demo passwords or do not seed in production.

## Rollback
Redeploy the previous image. Migrations are forward-only in this build; take a database backup
before every release that includes a migration.
