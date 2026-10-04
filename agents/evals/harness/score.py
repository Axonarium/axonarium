"""Scoring extractions against gold claims (plan, Quality and validation).

A predicted claim matches a gold claim when they name the same subject, predicate, object and species. On matched
claims, the method (evidence class), result and sign are scored as field accuracy. Unmatched predictions that are a
gold claim reversed count as direction errors, and those that match one in another species as species errors.
"""

from collections import defaultdict
from dataclasses import dataclass, field

FIELDS = ("evidence_class", "result", "sign")


def key(claim) -> tuple[str, str, str, str]:
    return claim.subject.id, claim.predicate, claim.object.id, claim.species


@dataclass
class Tally:
    predicted: int = 0
    gold: int = 0
    matched: int = 0
    direction_errors: int = 0
    species_errors: int = 0
    gold_absent: int = 0
    matched_absent: int = 0
    field_right: dict[str, int] = field(default_factory=lambda: dict.fromkeys(FIELDS, 0))

    def add(self, other: "Tally") -> None:
        for name in ("predicted", "gold", "matched", "direction_errors", "species_errors", "gold_absent", "matched_absent"):
            setattr(self, name, getattr(self, name) + getattr(other, name))
        for name in FIELDS:
            self.field_right[name] += other.field_right[name]

    def metrics(self) -> dict:
        ratio = lambda a, b: round(a / b, 4) if b else None  # noqa: E731
        precision, recall = ratio(self.matched, self.predicted), ratio(self.matched, self.gold)
        f1 = round(2 * precision * recall / (precision + recall), 4) if precision and recall else None
        return {"precision": precision, "recall": recall, "f1": f1,
                "field_accuracy": {name: ratio(self.field_right[name], self.matched) for name in FIELDS},
                "absent_recall": ratio(self.matched_absent, self.gold_absent),
                "counts": {"predicted": self.predicted, "gold": self.gold, "matched": self.matched,
                           "direction_errors": self.direction_errors, "species_errors": self.species_errors}}


def score_paper(gold: list, predicted: list) -> Tally:
    """One paper's tally. Claims with the same key count once; a field is right if any gold claim with that key has
    the predicted value (a connection can be shown by several methods)."""
    gold_by_key: dict[tuple, list] = defaultdict(list)
    for claim in gold:
        gold_by_key[key(claim)].append(claim)
    predicted_by_key: dict[tuple, list] = defaultdict(list)
    for claim in predicted:
        predicted_by_key[key(claim)].append(claim)
    tally = Tally(predicted=len(predicted_by_key), gold=len(gold_by_key))
    tally.gold_absent = sum(any(c.result == "absent" for c in claims) for claims in gold_by_key.values())
    for k, claims in predicted_by_key.items():
        if k in gold_by_key:
            tally.matched += 1
            expected = gold_by_key[k]
            tally.matched_absent += any(c.result == "absent" for c in expected) and any(c.result == "absent" for c in claims)
            for name in FIELDS:
                tally.field_right[name] += any(getattr(c, name) in {getattr(e, name) for e in expected} for c in claims)
            continue
        subject, predicate, obj, species = k
        if (obj, predicate, subject, species) in gold_by_key:
            tally.direction_errors += 1
        elif any(g[:3] == (subject, predicate, obj) for g in gold_by_key):
            tally.species_errors += 1
    return tally
