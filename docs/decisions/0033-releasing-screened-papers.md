---
status: accepted
date: 2026-10-15
decision-makers: Tyler Banks
consulted: Claude (review queue, #116)
---

# Releasing screened papers, and dropping article-history lines

## Context and Problem Statement

The hidden-text screen (ADR 0023) flags a paper when any paragraph scores 0.92 or more on the prompt-injection classifier, and a flagged paper is never sent to a model. ADR 0023 expected the threshold might need tuning once extraction measured the false-positive rate. By the end of the open-access backlog, 30 of the 347 papers fetched had been screened out, roughly 1 in 12, and every finding looked harmless. A typical run's findings (Literature run 37986233180) were eNeuro's article-history line ("Received 2023 Sep 20; Revised 2024 Feb 8; Accepted …", 4 of 10 findings, scoring 0.93 to 0.99), section and figure titles ("Pre-choice inhibition", "substantia innominata", both 1.00), a protocol step, an equation, and a reviewer's comment printed with an eNeuro paper. #134 already drops the peer review printed with eLife papers. How should the rest be let through without opening a way past the screen (#116, question 3)?

## Considered Options

* Drop article-history lines from both the screen and the model, and let the maintainer release a paper by key after reading its findings
* Also skip figure titles, headings and table- or sequence-like paragraphs before scoring
* Raise the threshold for short paragraphs

## Decision Outcome

Chosen option: "drop article-history lines, and release by key". The screen's rule is that what it reads is what the model reads. Skipping a figure title or heading when scoring while the model still reads it would let an instruction placed there through, and short paragraphs are where a planted instruction would be. So nothing the model reads goes unscored, and the threshold stays at 0.92.

* **Article-history lines** are dropped before scoring and from the text the model reads. Only a whole line of publication events and dates matches (`Received`, `Revised`, `Accepted`, `Prepublished`, `Published` and `Collection date`, each with a date), so no other text can hide in one. Invisible characters in such a line are still found first. The clean fixture now holds one, so CI's `screen` job checks with the real classifier that it is dropped.
* **Release by key:** `corpus/released.csv` (key, findings digest, date, note) names papers the maintainer has read and released. A flagged paper is sent anyway when its key is listed with the digest of its current findings. The digest is 16 hex digits of a SHA-256 over each finding's layer and whole flagged text, without the classifier's score. A paper whose flagged text changes is therefore held again, and a new runtime's rounding doesn't change the digest. The file is code-owned, so only the maintainer's review adds a row.
* **The run's report** now shows every finding's whole flagged text, not a 160-character excerpt, so the maintainer reads all of what they release. Each screened paper's `key,digest` row is listed under **To release**, and a released paper under **Released**. Verification honours the same list.
* The eval harness is unchanged: a screened gold paper still counts as missed.

### Consequences

* Good, because the most common false positive goes away without weakening the screen, and the rest are released by a person who has read them.
* Good, because a release is tied to the exact text that was read: a change to that text needs a new reading.
* Bad, because each other false positive still costs the maintainer a reading, and a released paper waits for a `--redo` run.
* Neutral: a classifier that does better on short scientific text would remove most of these readings, but would need its own ADR (ADR 0023's "Adopt, don't invent").
