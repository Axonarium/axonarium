---
status: accepted
date: 2026-10-03
decision-makers: Tyler Banks
---

# Human review for deletions and retractions

## Context and Problem Statement

The plan's merge rules let claim pull requests auto-merge on green CI, but deletions and retractions always need human review. CODEOWNERS can't tell a deletion from an addition, and agents act through the maintainer's GitHub account, so any label they could be asked to wait for they could also add. How does a pull request that deletes or retracts a claim come to require the maintainer?

## Considered Options

* A retractions log, `data/retractions.yaml`, owned by the maintainer through CODEOWNERS, that every deletion or retraction must add to
* Never deleting claim files; retraction is only a status change
* A label, such as `human-reviewed`, that CI checks for

## Decision Outcome

Chosen option: "a retractions log", because it puts every such pull request on a maintainer-owned file, which the branch rules already send to code-owner review, and it leaves a permanent record of what was removed and why.

The `checks changes` step in the required CI job fails when:

* a claim is deleted without a new `deleted` entry;
* a claim's status becomes `retracted` without a new `retracted` entry;
* existing entries are edited, reordered or removed.

Moving a claim file isn't a deletion.

### Consequences

* Good, because deletions and retractions can't auto-merge, and the log is the audit trail the plan asks for ("flagged, not silently deleted").
* Good, because it needs no new GitHub feature: CODEOWNERS and the required `checks` job do the work.
* Bad, because a pull request that only removes duplicates still waits for the maintainer.
* Neutral: a label gate was rejected because anyone with write access, agents included, can add labels.
