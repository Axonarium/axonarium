"""The gold curation tool (sprint 0.5a): a local page for curating the gold set quickly.

    uv run --directory .. python -m ingest.lexicon --out .cache/lexicon.json    # once: the atlases' regions
    uv run python -m curate                                                    # then open http://127.0.0.1:8765

It shows a paper's full text (by PMC ID, from Europe PMC) beside a claim form with region search over the pinned
atlases, and saves each paper as `papers/<name>.yaml` in the eval harness's gold format (agents/evals/README.md).
Drafts go to .cache/gold-drafts/ unless --out names another folder; the maintainer reviews them and commits them to
the gold set. It runs only on this machine (127.0.0.1) and never writes into agents/evals/gold/ on its own.
"""
