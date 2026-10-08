"""The literature pipeline (ADR 0028): triage, extraction and verification of the corpus's papers.

    uv run python -m pipeline triage --limit 200          # abstracts, on the Batch API
    uv run python -m pipeline triage --limit 5 --now      # a small trial with live calls, at full price

Every step reads and writes files in the repository: the corpus manifest, its ledgers (corpus/triage.csv) and, from
sprint 2.3, claim files. A paper is never paid for twice with the same prompt.
"""
