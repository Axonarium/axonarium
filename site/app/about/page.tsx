import type { Metadata } from "next";

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
