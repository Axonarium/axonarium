import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "About" };

const REPO = "https://github.com/axonarium/axonarium";

export default function About() {
  return (
    <article className="max-w-2xl space-y-6 [&_a]:underline [&_a]:underline-offset-4 [&_h2]:pt-4 [&_h2]:text-xl [&_h2]:font-semibold [&_p]:text-muted-foreground">
      <h1 className="text-3xl font-semibold tracking-tight">About Axonarium</h1>
      <p>
        Axonarium is an open, evidence-graded knowledge base of neural connectivity. Every connection is an aggregate of
        cited claims, each tagged with species, method and confidence. It starts with the rodent amygdala and its human
        homologues, and grows one circuit at a time toward whole-brain and brain–body coverage.
      </p>
      <h2>What is in it today</h2>
      <p>
        The mouse amygdala&apos;s connections at the level of brain regions, from the{" "}
        <a href="https://connectivity.brain-map.org/">Allen Mouse Brain Connectivity Atlas</a> (
        <a href="https://doi.org/10.1038/nature13186">Oh et al. 2014</a>): every target of anterograde tracer
        injected into an amygdala nucleus of a wild-type mouse, and every amygdala nucleus that injections elsewhere
        label. Each experiment and target is one claim, with its projection density. See them on the{" "}
        <Link href="/brain">3D brain and network</Link>, in the <Link href="/explore">connection table</Link>, or
        region by region. Regions come from the Allen mouse and human atlases via BrainGlobe, mapped to UBERON (
        <Link href="/atlases">Atlases</Link>).
      </p>
      <h2>Reading the evidence</h2>
      <p>
        A connection is never typed by hand: it is computed from its claims, and opens them. A claim is{" "}
        <em>accepted</em> when at least half of the injected tracer was in the region it names, and{" "}
        <em>proposed</em> when most of it spread elsewhere; regions that received tracer themselves are never
        counted as targets. Densities pool both hemispheres. Claims from the Allen atlas are made when the site is
        built and shown here with their citation, but are not redistributed in the downloadable data, following the
        Allen Institute&apos;s terms.
      </p>
      <h2>What comes next</h2>
      <p>
        Rat connectivity, human homology, cell-type-specific connections, and claims from the published literature,
        drafted by AI agents and checked by independent verifier agents and human audit. Progress is tracked in the{" "}
        <a href={`${REPO}/blob/main/STATUS.md`}>status page</a> and the sprint cards on GitHub.
      </p>
      <h2>How it is built</h2>
      <p>
        The knowledge lives as plain YAML files in a <a href={REPO}>public GitHub repository</a>. Humans and AI agents
        change it only through pull requests, which must pass automated checks: the schema, every identifier and
        citation looked up in its registry, retracted papers flagged, and deletions reviewed by a person. This site and
        its database are rebuilt from those files on every merge.
      </p>
      <h2>Licences</h2>
      <p>
        Project-curated data is licensed under CC BY 4.0, and code under Apache-2.0. Data from other sources keeps its
        own terms, recorded per source.
      </p>
      <h2>Citing</h2>
      <p>
        Cite the repository (see <a href={`${REPO}/blob/main/CITATION.cff`}>CITATION.cff</a>) and the original papers
        behind the claims you use; every claim links to its source.
      </p>
      <h2>Contributing</h2>
      <p>
        Read <a href={`${REPO}/blob/main/CONTRIBUTING.md`}>CONTRIBUTING.md</a> and the open sprint cards on GitHub.
      </p>
    </article>
  );
}
