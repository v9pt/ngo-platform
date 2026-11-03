# NGO donation platform and women's schemes finder

A take-home build: donors give to campaigns and get numbered receipts; women find government
schemes they may qualify for, with the reasons shown. Hindi first, light/dark/system theme.

Design and decisions: [docs/TDD.md](docs/TDD.md). Deployment: [deployment.md](deployment.md).

## Stack
Next.js 16 (TypeScript) frontend, FastAPI + SQLAlchemy backend, PostgreSQL 16, Alembic migrations.

## Run it locally
Backend (Python 3.12; tests also pass on 3.11):

```bash
cd backend
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
export DATABASE_URL='postgresql+psycopg://postgres@localhost:5433/ngo_test'
alembic upgrade head
python -m app.seed                      # demo accounts, schemes, campaigns
export JWT_SECRET="$(python -c 'import secrets;print(secrets.token_urlsafe(48))')"
export PAN_ENCRYPTION_KEY="$(python -c 'from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())')"
export GATEWAY_WEBHOOK_SECRET="$(python -c 'import secrets;print(secrets.token_urlsafe(48))')"
uvicorn app.main:create_app --factory --reload
```

PDF receipts need pango (`brew install pango` on macOS, then run with
`DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`; the Docker image installs it).

Frontend:

```bash
cd frontend
npm install
API_URL=http://localhost:8000 GATEWAY_WEBHOOK_SECRET=<same as API> npm run dev
```

Demo accounts (public demo credential, not a secret): `admin@`, `editor@`, `donor@demo.example`,
password `DemoPass#2026`.

## Checks
```bash
cd backend && ruff check . && ruff format --check . && mypy app tests && python -m pytest -q
cd frontend && npm run lint && npm run build
```
Tests run against a real Postgres (set `TEST_DATABASE_URL`) and build the schema with the real
migration. CI runs the same commands (`.github/workflows/ci.yml`).

## What is demo-grade
Sample scheme data, the payment gateway (a signed-webhook mock), the trust's PAN and 80G number,
and the 10BD export are placeholders. See the assumptions list in the TDD.
