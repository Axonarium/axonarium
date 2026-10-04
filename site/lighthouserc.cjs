// The performance budget (sprint 3.5, ADR 0025): Lighthouse's default mobile emulation, a mid-range phone on a slow
// 4G connection, on one page of each kind, three runs each, judged on the median run. Pages show real data: their IDs
// come from the snapshot the build read. Run with `npx @lhci/cli@0.15.1 autorun --config=lighthouserc.cjs`.
/* eslint-disable @typescript-eslint/no-require-imports -- Lighthouse CI reads its config as CommonJS */
const { readFileSync } = require("node:fs");
const { join } = require("node:path");

const { tables } = JSON.parse(readFileSync(join(__dirname, "snapshot", "snapshot.json"), "utf-8"));
const claim = tables.connectivity_claims.find((c) => c.status === "accepted") ?? tables.connectivity_claims[0];
const region = tables.regions.find((r) => r.amygdala) ?? tables.regions[0];
const BASE = "http://localhost:3100";

const PAGES = [
  "/explore",
  "/regions",
  `/regions/${encodeURIComponent(region.id)}`,
  `/claims/${claim.id}`,
  `/edges/${encodeURIComponent(tables.edges[0].id)}`,
];

// Pages of text and tables: Web Vitals' "good" thresholds, and a weight a phone on 4G loads quickly. Largest paint
// gets 3 s rather than 2.5: in the lab it includes the server's render on a CI runner, and today's pages land at
// 2.1–2.8 s.
const PAGE = {
  "categories:performance": ["error", { minScore: 0.9 }],
  "categories:accessibility": ["error", { minScore: 1 }],
  "largest-contentful-paint": ["error", { maxNumericValue: 3000 }],
  "cumulative-layout-shift": ["error", { maxNumericValue: 0.1 }],
  "total-blocking-time": ["error", { maxNumericValue: 200 }],
  "total-byte-weight": ["error", { maxNumericValue: 1_000_000 }],
};

// Pages with the 3D brain (the home page's preview, and /brain): three.js and the meshes are heavy by nature, so the
// budget keeps them stable while they load, and stops them growing. Blocking time and the performance score aren't
// judged: CI's runners have no GPU, so WebGL renders in software on the main thread, frame after frame, and Lighthouse
// measures that (about 160 s), not what a phone's GPU does.
const THREE_D = {
  "categories:accessibility": ["error", { minScore: 1 }],
  "largest-contentful-paint": ["error", { maxNumericValue: 4000 }],
  "cumulative-layout-shift": ["error", { maxNumericValue: 0.1 }],
  "total-byte-weight": ["error", { maxNumericValue: 6_000_000 }],
};

module.exports = {
  ci: {
    collect: {
      startServerCommand: "npm run start -- -p 3100",
      startServerReadyPattern: "Ready",
      url: ["/", "/brain", ...PAGES].map((path) => BASE + path),
      numberOfRuns: 3,
    },
    assert: {
      assertMatrix: [
        { matchingUrlPattern: ":3100/(brain)?$", aggregationMethod: "median-run", assertions: THREE_D },
        { matchingUrlPattern: ":3100/(?!(brain)?$)", aggregationMethod: "median-run", assertions: PAGE },
      ],
    },
    upload: { target: "filesystem", outputDir: ".lighthouseci" },
  },
};
