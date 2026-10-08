"""Verification (sprint 2.4): each extracted claim judged by a separate prompt, its verdict written into the claim."""

import yaml

from pipeline import extract, verify
from pipeline.corpus import Ledger
from pipeline.llm import Result
from pipeline.tests.test_extract import LEXICON, PAPERS, TRIAGED, FakeRun, text


def lexicon():
    return extract.Lexicon(LEXICON["atlases"], LEXICON["neuron_types"])


def extracted(tmp_path):
    claims = tmp_path / "claims"
    extract.extract(PAPERS, FakeRun(), 10, lexicon(), classify=None, today="2026-10-08",
                    ledger=Ledger(tmp_path / "extracted.csv", extract.LEDGER.columns), triaged=TRIAGED, claims_dir=claims, text=text)
    return claims


class Judge:
    """Agrees with claim 1, disagrees with claim 2, is unsure of 3, and leaves out the rest."""

    model, name, batch = "claude-opus-5-5", "anthropic:claude-opus-5-5", True

    def __init__(self):
        self.sent = []

    def run(self, requests):
        self.sent += requests
        verdicts = verify.Verdicts(verdicts=[
            verify.ClaimVerdict(claim=1, verdict="agree", note="Figure 1 shows  it."),
            verify.ClaimVerdict(claim=2, verdict="disagree", note="The paper traced the reverse direction."),
            verify.ClaimVerdict(claim=3, verdict="unsure", note="Only a figure shows it."),
        ])
        return {r.id: Result(verdicts, "end_turn", {"input_tokens": 20_000, "output_tokens": 1_000}) for r in requests}


def test_verdicts_are_written_into_the_claims(tmp_path):
    claims = extracted(tmp_path)
    judge = Judge()
    summary = verify.verify(PAPERS, judge, 10, lexicon(), classify=None, today="2026-10-09", claims_dir=claims, text=text)
    assert len(judge.sent) == 1  # one request per paper, listing its claims
    request = judge.sent[0].text
    assert request.startswith("PMC1\n\n## Claims to check\n\nClaim 1:")
    assert '- subject: MBA:295 (BLA, Basolateral amygdalar nucleus), called "name of MBA:295" in the paper' in request
    assert "- object: UBERON:0002883, called" in request  # UBERON terms have no atlas name
    assert judge.sent[0].system.startswith("You check connectivity claims")

    records = [yaml.safe_load(p.read_text(encoding="utf-8")) for p in sorted(claims.glob("*.yaml"))]
    judged = [r for r in records if "verification" in r]
    assert sorted(r["verification"]["verdict"] for r in judged) == ["agree", "disagree", "unsure"]
    first = next(r for r in judged if r["verification"]["verdict"] == "agree")
    assert first["verification"] == {"by": "agent", "role": "verifier", "model": "claude-opus-5-5", "prompt": "verify@0.1.0",
                                     "verdict": "agree", "date": "2026-10-09"}
    assert first["extra"]["verify.note"] == "Figure 1 shows it." and first["status"] == "proposed"
    assert list(first) == ["id", "subject", "predicate", "object", "species", "evidence_class", "result", "sign", "source",
                           "paraphrase", "curation", "verification", "status", "extra"]
    assert summary["agree"] == 1 and summary["disagree"] == 1 and summary["unsure"] == 1
    assert len(summary["unjudged"]) == 1 and "got no verdict" in summary["unjudged"][0]
    assert summary["remaining"] == 1  # the paper with the unjudged claim

    again = Judge()
    verify.verify(PAPERS, again, 10, lexicon(), classify=None, today="2026-10-10", claims_dir=claims, text=text)
    assert again.sent[0].text.count("Claim ") == 1  # only the claim without a verdict is sent again


def test_papers_whose_text_is_flagged_or_unreadable_are_skipped(tmp_path):
    claims = extracted(tmp_path)

    def flagged(paper):
        raise SyntaxError("not XML")

    summary = verify.verify(PAPERS, Judge(), 10, lexicon(), classify=None, claims_dir=claims, text=flagged)
    assert summary["sent"] == 0 and summary["skipped"] == ["doi:10.1/a: its text couldn't be read (SyntaxError)"]
    assert all("verification" not in yaml.safe_load(p.read_text(encoding="utf-8")) for p in claims.glob("*.yaml"))
