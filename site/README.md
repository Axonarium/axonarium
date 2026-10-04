# Site

The Axonarium explorer: Next.js 16 (App Router), Tailwind 4 and shadcn/ui, reading the public, read-only Supabase tables that `python -m build` fills ([build/README.md](../build/README.md)).

```bash
npm ci
NEXT_PUBLIC_SUPABASE_URL=https://pspctylgsozeozyamykd.supabase.co \
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=sb_publishable_… npm run dev
```

Both variables are public by design (the key can only read). When Supabase can't answer (a paused free project, an outage) or isn't configured, every query is answered from `snapshot/snapshot.json`, the deploy's snapshot of the same database, bundled with every server route ([ADR 0017](../docs/decisions/0017-static-fallback.md)). It holds Allen-derived rows, so it is never committed or put in `public/`. To try the site without Supabase, write one: `uv run python -m build --snapshot site/snapshot/snapshot.json` from the repository root. With neither, pages render with a "data unavailable" notice.

| Command | Does |
| --- | --- |
| `npm run lint` | ESLint (Next.js rules) |
| `npm run typecheck` | Generates route types, then `tsc` |
| `npm test` | Vitest unit tests |
| `npm run build` | Production build |

Deployed to Vercel by `.github/workflows/deploy.yml` on every merge to `main` (Vercel CLI, prebuilt). Pull requests run the commands above in CI and never deploy. Read [AGENTS.md](AGENTS.md) before changing Next.js code: this version's APIs differ from older ones.
