# Changelog

Format: [Keep a Changelog](https://keepachangelog.com). Dated, since this is not a versioned release.

## 2026-11-03

### Added
- 80G certificates: PAN entry before payment, encrypted at rest; receipts without a PAN say they are plain.
- Test-card payment page with declined, low-funds and blocked foreign-card outcomes, and retry.
- Monthly giving: one mandate per first gift, a repeat-safe charge run, and cancelling from the account.
- Typed questions in Hindi or English pre-fill the finder; where Claude and the keyword reader disagree the field stays blank.
- Hand-written summaries, through the same checks and approval as AI drafts.
- Helpline call-backs on every result, with consent, plus a staff queue.
- Scheme admin: create, edit every field, build rules, see history. Publishing is blocked until a scheme is complete.
- Campaign report screen and CSV link. Browsing by need and district. Hindi for all public scheme text.
- Seed data with a real giving history. Unit tests, browser tests, axe checks and a receipt load script.
- TDD as a PDF and a script that builds the submission zip.

### Changed
- New design system, home page led by the finder, and loading, empty and error states throughout.
- Finder results now explain rules in plain words instead of showing field names and operators.
- Failed staff actions show the reason in place and keep what was typed.
- The webhook secret left the frontend: the API now decides test-card outcomes.
- The default Claude model is now claude-opus-5-5, and refused or cut-off replies count as failures.

### Fixed
- Successful logins no longer use up the login rate limit.
- The API now commits before it responds. Before, a page could refresh and read the old row, and a failed commit would already have reported success.

### Removed
- The simulate-payment server action.
