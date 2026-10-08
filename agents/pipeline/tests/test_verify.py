"""Verification (sprint 2.4): each extracted claim judged by a separate prompt, its verdict written into the claim."""

import yaml

from pipeline import extract, verify
from pipeline.corpus import Ledger, Redo
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
    assert first["verification"] == {"by": "agent", "role": "verifier", "model": "claude-opus-5-5", "prompt": "verify@0.2.0",
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


def test_a_collected_batch_is_used_only_for_the_claims_it_listed(tmp_path):
    from pipeline.llm import request_id

    claims = extracted(tmp_path)
    (paper, listed), = verify.unverified(claims, "verify@0.2.0", verify.paper_index(PAPERS)).values()
    then = request_id(verify.request_key((paper, listed)))
    assert then == request_id(verify.request_key((paper, list(listed))))  # the same claims, the same request

    judge = Judge()
    judge.known = lambda: {request_id(verify.request_key((paper, listed[:-1])))}  # a batch that listed one claim fewer
    summary = verify.verify(PAPERS, judge, 10, lexicon(), classify=None, today="2026-10-09", claims_dir=claims, text=text)
    assert judge.sent == [] and summary["sent"] == 0  # its numbering would put verdicts on the wrong claims

    judge.known = lambda: {then}
    verify.verify(PAPERS, judge, 10, lexicon(), classify=None, today="2026-10-09", claims_dir=claims, text=text)
    assert [r.id for r in judge.sent] == [then]


class Silent(Judge):
    """Answers, but judges none of the claims."""

    def run(self, requests):
        self.sent += requests
        return {r.id: Result(verify.Verdicts(verdicts=[]), "end_turn", {"input_tokens": 20_000}) for r in requests}


def test_the_ledger_records_each_request_and_sets_aside_claims_never_judged(tmp_path):
    claims = extracted(tmp_path)
    ledger = Ledger(tmp_path / "verified.csv", verify.LEDGER.columns)
    for day in ("2026-10-09", "2026-10-10"):
        verify.verify(PAPERS, Silent(), 10, lexicon(), classify=None, today=day, claims_dir=claims, text=text, ledger=ledger)
    row = ledger.read()["doi:10.1/a"]
    assert row["outcome"] == "judged" and row["judged"] == "0" and row["claims"] == "4" and row["attempts"] == "2"
    third = Silent()
    summary = verify.verify(PAPERS, third, 10, lexicon(), classify=None, today="2026-10-11", claims_dir=claims, text=text,
                            ledger=ledger)
    assert third.sent == [] and summary["set_aside"] == ["doi:10.1/a: 4 claim(s)"]

    judge = Judge()  # asked for again: judged now, and judged claims are never sent again
    verify.verify(PAPERS, judge, 10, lexicon(), classify=None, today="2026-10-11", claims_dir=claims, text=text, ledger=ledger,
                  redo=Redo(("10.1/a",)))
    assert len(judge.sent) == 1 and ledger.read()["doi:10.1/a"]["judged"] == "3"


def test_a_new_verifier_prompt_judges_again_only_when_asked_and_never_over_a_person(tmp_path):
    claims = extracted(tmp_path)
    verify.verify(PAPERS, Judge(), 10, lexicon(), classify=None, today="2026-10-09", claims_dir=claims, text=text)
    person = next(p for p in sorted(claims.glob("*.yaml")) if "verification" in yaml.safe_load(p.read_text(encoding="utf-8")))
    record = yaml.safe_load(person.read_text(encoding="utf-8"))
    record["verification"] = {**record["verification"], "by": "human", "role": "curator"}
    person.write_text(yaml.safe_dump(record, sort_keys=False), encoding="utf-8")
    index = verify.paper_index(PAPERS)
    assert sum(len(c) for _, c in verify.unverified(claims, "verify@0.3.0", index).values()) == 1  # the claim left out
    redone = verify.unverified(claims, "verify@0.3.0", index, Redo(("older",)))
    assert sum(len(c) for _, c in redone.values()) == 3  # two the agent judged, and the one left out; not the person's


def test_the_verifier_reads_strength_and_numbers():
    record = {"subject": {"id": "MBA:295"}, "predicate": "functionally_connects_to", "object": {"id": "MBA:536"}, "species": "NCBITaxon:10090",
              "evidence_class": "paired_recording", "result": "present", "sign": "excitatory", "strength": "strong",
              "measurements": [{"quantity": "connection_probability", "value": 0.4, "unit": "1", "n": 30},
                               {"quantity": "conduction_delay", "value": 3.2, "unit": "ms", "sem": 0.4}],
              "source": {"locator": "Fig. 4"}, "paraphrase": "p"}
    text = verify.describe(1, record, lexicon())
    assert "- strength: strong" in text
    assert "- number: connection probability 0.4 (n = 30)" in text and "- number: conduction delay 3.2 ms (SEM 0.4)" in text
