# Frontend

Next.js site for the trust. See the [root README](../README.md) and [deployment.md](../deployment.md).

- `src/lib/finder.ts`: questions and plain-language rule text. Pure and unit-tested.
- `src/lib/i18n.ts`: Hindi and English strings for public screens.
- `src/app/globals.css`: the design tokens. Components use token roles, never raw colours.
- `e2e/`: Playwright flows and axe checks. They need the API on :8000 and the site on :3000.
