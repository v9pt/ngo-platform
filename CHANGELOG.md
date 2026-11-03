# Changelog

All notable changes to this project are documented here, following
[Keep a Changelog](https://keepachangelog.com).

## [Unreleased]

### Added
- API skeleton: validated config, RFC 7807 errors, per-request transactions, health and readiness.
- Database schema with invariants in the DB: immutable receipts, unique receipt numbers per
  financial year, minimum donation amount, approval-recorded check for summaries.
- Account auth with roles (donor, editor, admin): argon2 passwords, httpOnly session cookie,
  login rate limiting, generic auth errors.
- PAN format validation, masking and encryption at rest.
- Idempotent seed data: demo accounts, seven illustrative schemes, three campaigns.
- Receipt issuing: one transaction, gapless numbers per financial year, replay-safe; verified with 200 parallel payments.
- Donation API (account required, idempotent via `Idempotency-Key`) and HMAC-signed mock gateway webhook that fails closed.
