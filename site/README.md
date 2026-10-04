# Site

The Axonarium explorer: Next.js 16 (App Router), Tailwind 4 and shadcn/ui, reading the public, read-only Supabase tables that `python -m build` fills ([build/README.md](../build/README.md)).

```bash
npm ci
NEXT_PUBLIC_SUPABASE_URL=https://pspctylgsozeozyamykd.supabase.co \
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=sb_publishable_… npm run dev
```

Both variables are public by design (the key can only read). When Supabase can't answer (a paused free project, an outage) or isn't configured, every query is answered from `snapshot/snapshot.json`, the deploy's snapshot of the same database, bundled with every server route ([ADR 0017](../docs/decisions/0017-static-fallback.md)). It holds Allen-derived rows, so it is never committed or put in `public/`. To try the site without Supabase, write one: `uv run python -m build --snapshot site/snapshot/snapshot.json` from the repository root. With neither, pages render with a "data unavailable" notice.

**Submissions** (Supports and Contradicts on each claim page; [ADR 0024](../docs/decisions/0024-evidence-buttons.md)) open once three more keys are set. Until then the buttons are hidden and `POST /api/submissions` answers 503.

| Variable | Where | What |
| --- | --- | --- |
| `NEXT_PUBLIC_TURNSTILE_SITE_KEY` | GitHub variable (the deploy's build) | The Cloudflare Turnstile widget's site key; public |
| `TURNSTILE_SECRET_KEY` | Vercel, production, sensitive | Turnstile's secret key, for siteverify; also keys the submitter hash |
| `SUPABASE_SECRET_KEY` | Vercel, production, sensitive | Supabase's secret key, the only key that may call `submit_evidence()` |

Locally, Cloudflare's test keys (site key `1x00000000000000000000AA`, secret `1x0000000000000000000000000000000AA`) always pass.

| Command | Does |
| --- | --- |
| `npm run lint` | ESLint (Next.js rules) |
| `npm run typecheck` | Generates route types, then `tsc` |
| `npm test` | Vitest unit tests |
| `npm run build` | Production build |
| `npm run e2e` | The accessibility budget: axe-core on every page type, phone and desktop, against the production build ([ADR 0025](../docs/decisions/0025-site-budgets.md)) |
| `npx @lhci/cli@0.15.1 autorun --config=lighthouserc.cjs` | The performance budget: Lighthouse on a mid-range phone, against the production build |

Both budgets need a build that read a snapshot (above); CI's `budgets` job makes one from the rebuild, with the meshes. Locally, `PLAYWRIGHT_CHROMIUM_PATH` points Playwright at a Chromium already installed, and `CHROME_PATH` does the same for Lighthouse.

Deployed to Vercel by `.github/workflows/deploy.yml` on every merge to `main` (Vercel CLI, prebuilt). Pull requests run the commands above in CI and never deploy. Read [AGENTS.md](AGENTS.md) before changing Next.js code: this version's APIs differ from older ones.
