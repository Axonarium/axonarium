# Site

The Axonarium explorer: Next.js 16 (App Router), Tailwind 4 and shadcn/ui, reading the public, read-only Supabase tables that `python -m build` fills ([build/README.md](../build/README.md)).

```bash
npm ci
NEXT_PUBLIC_SUPABASE_URL=https://pspctylgsozeozyamykd.supabase.co \
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=sb_publishable_… npm run dev
```

Both variables are public by design (the key can only read). Without them the pages render with a "data unavailable" notice.

| Command | Does |
| --- | --- |
| `npm run lint` | ESLint (Next.js rules) |
| `npm run typecheck` | Generates route types, then `tsc` |
| `npm test` | Vitest unit tests |
| `npm run build` | Production build |

Deployed to Vercel by `.github/workflows/deploy.yml` on every merge to `main` (Vercel CLI, prebuilt). Pull requests run the commands above in CI and never deploy. Read [AGENTS.md](AGENTS.md) before changing Next.js code: this version's APIs differ from older ones.
