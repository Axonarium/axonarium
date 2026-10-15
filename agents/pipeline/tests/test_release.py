"""Releasing a screened paper (ADR 0033): only for exactly the findings the maintainer read."""

from pipeline import extract, release
from pipeline.corpus import Ledger
from pipeline.tests.test_extract import LEXICON, PAPERS, TRIAGED, FakeRun
from screen import Finding, Screened


def test_a_screened_paper_goes_to_the_model_only_once_released_for_exactly_its_findings(tmp_path, monkeypatch):
    monkeypatch.setattr(release, "RELEASED", tmp_path / "released.csv")
    flagged = Screened("PMC1", (Finding("injection", "score 0.99", "Pre-choice inhibition", "Pre-choice inhibition"),))
    lexicon = extract.Lexicon(LEXICON["atlases"], LEXICON["neuron_types"])

    def run_once(name):
        run, ledger = FakeRun(), Ledger(tmp_path / f"ledger-{name}.csv", extract.LEDGER.columns)
        summary = extract.extract(PAPERS[:1], run, 10, lexicon, classify=None, today="2026-10-15", ledger=ledger,
                                  triaged=TRIAGED, claims_dir=tmp_path / name, text=lambda paper: flagged)
        return run, summary

    run, summary = run_once("held")
    assert run.sent == [] and summary["to_release"] == [f"doi:10.1/a,{flagged.digest}"]
    assert summary["screen_findings"] == ["doi:10.1/a: injection, score 0.99: Pre-choice inhibition"]

    (tmp_path / "released.csv").write_text(f"key,findings,date,note\ndoi:10.1/a,{'0' * 16},2026-10-15,another digest\n")
    assert run_once("stale")[0].sent == []  # released for other findings: held again

    (tmp_path / "released.csv").write_text(f"key,findings,date,note\ndoi:10.1/a,{flagged.digest},2026-10-15,a figure title\n")
    run, summary = run_once("released")
    assert [r.text for r in run.sent] == ["PMC1"] and summary["claims_written"] == 4
    assert summary["released"] == [f"doi:10.1/a: released for findings {flagged.digest}"] and summary["to_release"] == []


def test_verification_holds_a_screened_paper_unless_it_is_released(tmp_path, monkeypatch):
    from pipeline import verify
    from pipeline.tests.test_verify import Judge, extracted, lexicon

    monkeypatch.setattr(release, "RELEASED", tmp_path / "released.csv")
    claims = extracted(tmp_path)
    flagged = Screened("PMC1", (Finding("injection", "score 0.95", "substantia innominata", "substantia innominata"),))

    judge = Judge()
    summary = verify.verify(PAPERS, judge, 10, lexicon(), classify=None, claims_dir=claims, text=lambda paper: flagged)
    assert judge.sent == [] and summary["skipped"] == ["doi:10.1/a: the hidden-text screen flagged it"]

    (tmp_path / "released.csv").write_text(f"key,findings,date,note\ndoi:10.1/a,{flagged.digest},2026-10-15,a region name\n")
    summary = verify.verify(PAPERS, judge, 10, lexicon(), classify=None, claims_dir=claims, text=lambda paper: flagged)
    assert len(judge.sent) == 1 and summary["agree"] == 1
