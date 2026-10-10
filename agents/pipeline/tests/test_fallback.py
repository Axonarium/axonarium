"""Refused requests go to a second model in the same run, and each answer names the model that gave it (ADR 0028)."""

from types import SimpleNamespace

import pytest

from pipeline import cli, extract, triage
from pipeline.corpus import Ledger
from pipeline.llm import BatchPending, FallbackRunner, ReplayRunner, Request, Result, request_id, spend
from pipeline.tests.test_extract import LEXICON, PAPERS as FULL_TEXT, TRIAGED, draft, text
from pipeline.tests.test_triage import PAPERS, fetch

VERDICT = triage.Verdict(tests_connections=True, evidence=["anterograde_tracer"], species=["rat"], reason="Traces PRV.")


class Model:
    """Answers each request, or refuses those whose text says so; records what it was sent."""

    def __init__(self, model: str, answer, refuses: str | None = None, unanswered: bool = False, pending: bool = False):
        self.model, self.name, self.batch = model, f"anthropic:{model}", True
        self.answer, self.refuses, self.unanswered, self.pending = answer, refuses, unanswered, pending
        self.sent: list[Request] = []

    def run(self, requests):
        self.sent += requests
        if self.pending:
            raise BatchPending("msgbatch_9")
        usage = {"input_tokens": 1_000_000, "output_tokens": 100_000}
        return {r.id: Result(None, "expired", model=self.model) if self.unanswered
                else Result(None, "refusal", usage, "bio", self.model) if self.refuses and self.refuses in r.text
                else Result(self.answer, "end_turn", usage, model=self.model) for r in requests}


def test_refused_requests_go_to_the_fallback_and_keep_the_refusal():
    primary = Model("claude-opus-5-5", VERDICT, refuses="rabies")
    fallback = Model("claude-opus-5", VERDICT)
    run = FallbackRunner(primary, fallback)
    results = run.run([Request("a", "prompt", "AAV in the BLA"), Request("b", "prompt", "rabies from the CeA")])
    assert [r.id for r in fallback.sent] == ["b"] and run.retried == 1 and run.pending is None
    assert results["a"].model == "claude-opus-5-5" and results["a"].earlier == []
    assert results["b"].parsed == VERDICT and results["b"].model == "claude-opus-5"
    assert [(r.stop, r.model, r.detail) for r in results["b"].earlier] == [("refusal", "claude-opus-5-5", "bio")]
    assert run.name == "anthropic:claude-opus-5-5, refusals to anthropic:claude-opus-5" and run.model == "claude-opus-5-5"


def test_a_refusal_stands_when_the_fallback_refuses_too_or_never_answers():
    for fallback, model in ((Model("claude-opus-5", VERDICT, refuses="rabies"), "claude-opus-5"),
                            (Model("claude-opus-5", VERDICT, unanswered=True), "claude-opus-5-5")):
        results = FallbackRunner(Model("claude-opus-5-5", VERDICT, refuses="rabies"), fallback).run([Request("b", "p", "rabies")])
        assert results["b"].stop == "refusal" and results["b"].model == model


def test_a_fallback_batch_still_running_leaves_the_refusals_and_its_id():
    run = FallbackRunner(Model("claude-opus-5-5", VERDICT, refuses="rabies"), Model("claude-opus-5", VERDICT, pending=True))
    results = run.run([Request("a", "p", "AAV"), Request("b", "p", "rabies")])
    assert results["a"].parsed == VERDICT and results["b"].stop == "refusal" and run.pending == "msgbatch_9"


def test_spend_prices_each_answer_at_its_own_model():
    refused = Result(None, "refusal", {"input_tokens": 1_000_000}, model="claude-opus-5-5")
    answered = Result(VERDICT, "end_turn", {"input_tokens": 1_000_000, "output_tokens": 100_000}, model="claude-opus-5",
                      earlier=[refused])
    usage, dollars = spend([answered, Result(VERDICT, "end_turn", {"output_tokens": 100_000})], "claude-opus-5-5", batch=True)
    assert usage["input_tokens"] == 2_000_000 and usage["output_tokens"] == 200_000
    assert dollars == pytest.approx((4 + 5 + 2.5 + 2) / 2)
    assert spend([], "claude-opus-5-5", batch=True)[1] == 0 and spend([], "replay", batch=True)[1] is None
    assert spend([Result(VERDICT, "end_turn", {"input_tokens": 1}, model="unknown")], "claude-opus-5-5", True)[1] is None


def test_triage_records_the_model_that_answered_and_a_refusals_category(tmp_path):
    ledger = Ledger(tmp_path / "triage.csv", triage.LEDGER.columns)
    run = FallbackRunner(Model("claude-opus-5-5", VERDICT, refuses="AAV"), Model("claude-opus-5", VERDICT))
    summary = triage.triage(PAPERS[:2], run, limit=10, today="2026-10-08", ledger=ledger, abstract=fetch)
    rows = ledger.read()
    assert rows["doi:10.1/a"]["model"] == "claude-opus-5" and rows["doi:10.1/a"]["verdict"] == "in"
    assert rows["doi:10.1/b"]["model"] == "claude-opus-5-5" and rows["doi:10.1/b"]["verdict"] == "in"
    assert summary["model"] == "anthropic:claude-opus-5-5, refusals to anthropic:claude-opus-5"
    assert summary["cost"] == pytest.approx((4 + 2) / 2 * 2 + (5 + 2.5) / 2)  # a refusal and an answer on 5.5, an answer on 5

    refused = triage.row(PAPERS[0], Result(None, "refusal", detail="bio"), "abstract", "claude-opus-5", "p", "d")
    assert refused["verdict"] == "refusal" and refused["reason"] == "bio"


def test_extracted_claims_name_the_model_that_drafted_them(tmp_path):
    claims, ledger = tmp_path / "claims", Ledger(tmp_path / "extracted.csv", extract.LEDGER.columns)
    answer = extract.PaperClaims(claims=[draft("MBA:295", "MBA:536")])
    run = FallbackRunner(Model("claude-opus-5-5", answer, refuses="PMC1"), Model("claude-opus-5", answer))
    extract.extract(FULL_TEXT[:1], run, 10, extract.Lexicon(LEXICON["atlases"], LEXICON["neuron_types"]), classify=None,
                    today="2026-10-08", ledger=ledger, triaged=TRIAGED, claims_dir=claims, text=text)
    (record,) = [p.read_text(encoding="utf-8") for p in claims.glob("*.yaml")]
    assert "model: claude-opus-5\n" in record and ledger.read()["doi:10.1/a"]["model"] == "claude-opus-5"


def test_replayed_refusals_and_the_cli_fallback(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(triage, "LEDGER", Ledger(tmp_path / "triage.csv", triage.LEDGER.columns))
    monkeypatch.setattr(cli, "read_manifest", lambda: PAPERS[:1])
    monkeypatch.setattr(triage.europepmc, "abstract", fetch)
    first, second = tmp_path / "first", tmp_path / "second"
    for folder, answer in ((first, '{"refusal": "bio"}'), (second, VERDICT.model_dump_json())):
        folder.mkdir()
        (folder / f"{request_id('doi:10.1/a')}.json").write_text(answer)
    assert ReplayRunner(first, triage.Verdict).run([Request(request_id("doi:10.1/a"), "", "")])[request_id("doi:10.1/a")].detail == "bio"
    assert cli.main(["triage", "--model", f"replay:{first}", "--fallback", f"replay:{second}"]) == 0
    out = capsys.readouterr().out
    assert f"replay:{first}, refusals to replay:{second}" in out and "- in: 1" in out and "- refusals sent to fallback: 1" in out


def test_the_cli_picks_a_fallback_for_opus_5_5_only(monkeypatch, capsys):
    made, waits = [], []

    def runner(spec, *args, **kwargs):
        made.append(spec)
        waits.append(kwargs["wait_seconds"])
        return SimpleNamespace(model=spec.partition(":")[2], name=spec, batch=True, run=lambda requests: {})

    monkeypatch.setattr(cli, "runner", runner)
    monkeypatch.setattr(cli, "read_manifest", lambda: [])
    for argv, expected in ((["triage"], ["anthropic:claude-opus-5-5", "anthropic:claude-opus-5"]),
                           (["triage", "--fallback", "none"], ["anthropic:claude-opus-5-5"]),
                           (["triage", "--model", "anthropic:claude-opus-5"], ["anthropic:claude-opus-5"]),
                           (["triage", "--model", "anthropic:claude-sonnet-5-5", "--fallback", "anthropic:claude-opus-5"],
                            ["anthropic:claude-sonnet-5-5", "anthropic:claude-opus-5"])):
        made.clear()
        assert cli.main(argv) == 0
        assert made == expected, argv
    waits.clear()
    assert cli.main(["triage", "--wait", "45"]) == 0 and waits == [45 * 60, 45 * 60]  # both models share one wait
    waits.clear()
    assert cli.main(["triage", "--wait", "-5", "--fallback", "none"]) == 0 and waits == [0]


def test_the_cli_tells_how_to_collect_a_fallback_batch_still_running(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(triage, "LEDGER", Ledger(tmp_path / "triage.csv", triage.LEDGER.columns))
    monkeypatch.setattr(cli, "read_manifest", lambda: PAPERS[:1])
    monkeypatch.setattr(triage.europepmc, "abstract", fetch)
    models = iter([Model("claude-opus-5-5", VERDICT, refuses="AAV"), Model("claude-opus-5", VERDICT, pending=True)])
    monkeypatch.setattr(cli, "runner", lambda *args, **kwargs: next(models))
    assert cli.main(["triage"]) == 0
    out = capsys.readouterr().out
    assert "--collect msgbatch_9 --model anthropic:claude-opus-5" in out
    assert (tmp_path / "triage.csv").read_text().count("refusal") == 1


def test_the_cli_collects_the_fallbacks_batch_beside_the_primarys(monkeypatch, capsys):
    made = []

    def runner(spec, *args, **kwargs):
        made.append((spec, kwargs.get("collect_batch")))
        return SimpleNamespace(model=spec.partition(":")[2], name=spec, batch=True, run=lambda requests: {},
                               known=lambda: set())

    monkeypatch.setattr(cli, "runner", runner)
    monkeypatch.setattr(cli, "read_manifest", lambda: [])
    assert cli.main(["triage", "--collect", "msgbatch_1", "--collect-fallback", "msgbatch_2"]) == 0
    assert made == [("anthropic:claude-opus-5-5", "msgbatch_1"), ("anthropic:claude-opus-5", "msgbatch_2")]
    made.clear()
    assert cli.main(["triage", "--collect", "msgbatch_1"]) == 0  # without it, the refusals are sent to the fallback again
    assert made == [("anthropic:claude-opus-5-5", "msgbatch_1"), ("anthropic:claude-opus-5", None)]
    for argv in (["triage", "--collect-fallback", "msgbatch_2"],
                 ["triage", "--collect", "msgbatch_1", "--collect-fallback", "msgbatch_2", "--fallback", "none"]):
        assert cli.main(argv) == 1
        assert "--collect-fallback goes with --collect" in capsys.readouterr().out


def test_refusals_take_the_answers_of_a_collected_fallback_batch():
    collected = Model("claude-opus-5", VERDICT)
    collected.run = lambda requests: {r.id: Result(VERDICT, "end_turn", model="claude-opus-5") if r.id == "b"
                                      else Result(None, "errored", detail="not in batch msgbatch_2") for r in requests}
    results = FallbackRunner(Model("claude-opus-5-5", VERDICT, refuses="rabies"), collected).run(
        [Request("b", "p", "rabies"), Request("c", "p", "rabies")])
    assert results["b"].parsed == VERDICT and results["b"].model == "claude-opus-5"
    assert results["c"].stop == "refusal"  # a refusal the collected batch doesn't hold stands
