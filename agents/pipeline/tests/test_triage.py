"""Triage (sprint 2.2a): abstracts in, verdicts in corpus/triage.csv out; never twice for the same prompt."""

import csv
import re
from types import SimpleNamespace

import pytest

from pipeline import cli, europepmc, extract, triage
from pipeline.corpus import MAX_ATTEMPTS, Ledger, Redo, aliases, due, identifier, recorded
from pipeline.llm import AnthropicRunner, BatchPending, Request, Result, choose, cost, parse, request_id

PAPERS = [
    {"key": "doi:10.1/a", "title": "BLA to CeA, traced", "europe_pmc": "MED:1", "full_text": "false"},
    {"key": "doi:10.1/b", "title": "A review", "europe_pmc": "MED:2", "full_text": "true"},
    {"key": "doi:10.1/c", "title": "No abstract here", "europe_pmc": "PPR:PPR3", "full_text": "true"},
    {"key": "doi:10.1/d", "title": "Unreachable", "europe_pmc": "MED:4", "full_text": "false"},
]
ABSTRACTS = {"MED:1": "We injected AAV into the BLA.", "MED:2": "We review amygdala circuits.", "PPR:PPR3": ""}


def fetch(europe_pmc: str) -> str:
    if europe_pmc not in ABSTRACTS:
        raise OSError("Europe PMC is down")
    return ABSTRACTS[europe_pmc]


class FakeRun:
    """Answers by what each request's text contains; records what it was sent."""

    model, name, batch = "claude-opus-5-5", "anthropic:claude-opus-5-5", True

    def __init__(self):
        self.sent: list[Request] = []

    def run(self, requests):
        self.sent += requests
        results = {}
        for request in requests:
            if "AAV" in request.text:
                verdict = triage.Verdict(tests_connections=True, evidence=["anterograde_tracer"], species=["mouse"],
                                         reason="Traces BLA outputs  with AAV.")
                results[request.id] = Result(verdict, "end_turn", {"input_tokens": 1000, "output_tokens": 100})
            elif "review" in request.text:
                verdict = triage.Verdict(tests_connections=False, evidence=[], species=["mouse", "rat"], reason="A review.")
                results[request.id] = Result(verdict, "end_turn", {"input_tokens": 1000, "output_tokens": 100})
            else:
                results[request.id] = Result(None, "refusal", {"input_tokens": 500})
        return results


def test_triage_records_verdicts_and_skips_what_is_decided(tmp_path):
    ledger = Ledger(tmp_path / "triage.csv", triage.LEDGER.columns)
    run = FakeRun()
    summary = triage.triage(PAPERS, run, limit=10, today="2026-10-08", ledger=ledger, abstract=fetch)
    rows = ledger.read()
    assert rows["doi:10.1/a"] == {"key": "doi:10.1/a", "verdict": "in", "basis": "abstract", "evidence": "anterograde_tracer",
                                       "species": "mouse", "reason": "Traces BLA outputs with AAV.", "attempts": "1",
                                       "model": "claude-opus-5-5", "prompt": "triage@0.1.0", "date": "2026-10-08"}
    assert rows["doi:10.1/b"]["verdict"] == "out" and rows["doi:10.1/b"]["species"] == "mouse;rat"
    assert rows["doi:10.1/c"]["verdict"] == "refusal" and rows["doi:10.1/c"]["basis"] == "title"
    assert "doi:10.1/d" not in rows  # its abstract couldn't be fetched: nothing was sent
    assert summary["in"] == 1 and summary["out"] == 1 and summary["failed"] == 1 and summary["unfetched"] == 1
    assert summary["usage"]["input_tokens"] == 2500 and summary["cost"] == pytest.approx((2500 * 4 + 200 * 20) / 1e6 / 2)
    assert summary["remaining"] == 2  # the refused paper and the unfetched one
    # Full-text papers go first; the title-only request says there is no abstract.
    assert [r.text.split("\n")[0] for r in run.sent] == ["Title: A review", "Title: No abstract here", "Title: BLA to CeA, traced"]
    assert run.sent[1].text.endswith("Abstract: (none)")

    again = FakeRun()
    triage.triage(PAPERS, again, limit=10, today="2026-10-09", ledger=ledger, abstract=fetch)
    assert [r.text.split("\n")[0] for r in again.sent] == ["Title: No abstract here"]  # only the failed one is retried
    with (tmp_path / "triage.csv").open(encoding="utf-8") as f:
        assert [r["key"] for r in csv.DictReader(f)] == ["doi:10.1/a", "doi:10.1/b", "doi:10.1/c"]

    # Refused twice, it is set aside: a third run sends nothing until someone asks for it again.
    third = FakeRun()
    summary = triage.triage(PAPERS, third, limit=10, today="2026-10-10", ledger=ledger, abstract=fetch)
    assert third.sent == [] and ledger.read()["doi:10.1/c"]["attempts"] == "2"
    assert summary["set_aside"] == ["doi:10.1/c: refusal"]
    fourth = FakeRun()
    triage.triage(PAPERS, fourth, limit=10, today="2026-10-10", ledger=ledger, abstract=fetch, redo=Redo(("10.1/c",)))
    assert [r.text.split("\n")[0] for r in fourth.sent] == ["Title: No abstract here"]


def test_a_new_prompt_version_reads_nothing_again_unless_asked(tmp_path):
    ledger = Ledger(tmp_path / "triage.csv", triage.LEDGER.columns)
    triage.triage(PAPERS, FakeRun(), limit=1, today="2026-10-08", ledger=ledger, abstract=fetch)
    assert list(ledger.read()) == ["doi:10.1/b"]
    prompt = tmp_path / "triage.md"
    prompt.write_text(triage.PROMPT.read_text(encoding="utf-8").replace("triage@0.1.0", "triage@0.2.0"), encoding="utf-8")
    run = FakeRun()
    triage.triage(PAPERS[:2], run, limit=10, today="2026-10-09", ledger=ledger, abstract=fetch, prompt=prompt)
    assert [r.text.split("\n")[0] for r in run.sent] == ["Title: BLA to CeA, traced"]  # only the paper never triaged
    assert ledger.read()["doi:10.1/b"]["prompt"] == "triage@0.1.0"

    older = FakeRun()  # asked for: every paper an earlier prompt decided
    triage.triage(PAPERS[:2], older, limit=10, today="2026-10-09", ledger=ledger, abstract=fetch, prompt=prompt,
                  redo=Redo(("older",)))
    assert [r.text.split("\n")[0] for r in older.sent] == ["Title: A review"]
    assert ledger.read()["doi:10.1/b"]["prompt"] == "triage@0.2.0" and ledger.read()["doi:10.1/b"]["attempts"] == "2"


def test_ledger_refuses_a_file_with_other_columns(tmp_path):
    (tmp_path / "triage.csv").write_text("key,verdict\n", encoding="utf-8")
    with pytest.raises(ValueError, match="columns"):
        Ledger(tmp_path / "triage.csv", triage.LEDGER.columns).read()


def message(text: str, stop: str = "end_turn", **usage):
    return SimpleNamespace(stop_reason=stop, content=[SimpleNamespace(type="thinking"), SimpleNamespace(type="text", text=text)],
                           usage=SimpleNamespace(input_tokens=usage.get("input", 10), output_tokens=usage.get("output", 5),
                                                 cache_read_input_tokens=None, cache_creation_input_tokens=0),
                           stop_details=SimpleNamespace(category="bio"))


def test_parse_validates_the_answer():
    good = '{"tests_connections": false, "evidence": [], "species": ["rat"], "reason": "A review."}'
    assert parse(message(good), triage.Verdict).parsed.species == ["rat"]
    assert parse(message(good), triage.Verdict).usage == {"input_tokens": 10, "output_tokens": 5,
                                                          "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}
    assert parse(message('{"tests_connections": "maybe"}'), triage.Verdict).stop == "invalid"
    assert parse(message("", "refusal"), triage.Verdict).detail == "bio"
    assert parse(message("{", "max_tokens"), triage.Verdict).stop == "max_tokens"


class FakeBatches:
    def __init__(self, ends_after: int):
        self.created, self.polls, self.ends_after = None, 0, ends_after

    def create(self, requests):
        self.created = requests
        return SimpleNamespace(id="msgbatch_1")

    def retrieve(self, batch_id):
        self.polls += 1
        return SimpleNamespace(processing_status="ended" if self.polls > self.ends_after else "in_progress")

    def results(self, batch_id):
        good = '{"tests_connections": true, "evidence": ["retrograde_tracer"], "species": ["rat"], "reason": "Traces."}'
        yield SimpleNamespace(custom_id="p00000", result=SimpleNamespace(type="succeeded", message=message(good)))
        yield SimpleNamespace(custom_id="p00001", result=SimpleNamespace(type="errored", error=SimpleNamespace(error="overloaded")))
        yield SimpleNamespace(custom_id="p00002", result=SimpleNamespace(type="expired"))


def client(batches):
    return SimpleNamespace(messages=SimpleNamespace(batches=batches))


def test_a_batch_is_submitted_with_structured_output_and_collected():
    batches = FakeBatches(ends_after=2)
    run = AnthropicRunner("claude-opus-5-5", triage.Verdict, "low", 8000, client=client(batches), sleep=lambda s: None)
    results = run.run([Request(f"p{i:05d}", "the prompt", f"paper {i}") for i in range(3)])
    params = batches.created[0]["params"]
    assert batches.created[0]["custom_id"] == "p00000" and params["model"] == "claude-opus-5-5"
    assert params["system"] == [{"type": "text", "text": "the prompt", "cache_control": {"type": "ephemeral"}}]
    assert params["output_config"]["effort"] == "low" and params["output_config"]["format"]["type"] == "json_schema"
    assert params["output_config"]["format"]["schema"]["additionalProperties"] is False
    assert results["p00000"].parsed.evidence == ["retrograde_tracer"]
    assert results["p00001"].stop == "errored" and "overloaded" in results["p00001"].detail
    assert results["p00002"].stop == "expired"
    assert {r.model for r in results.values()} == {"claude-opus-5-5"}  # each result names the model it went to


class Clock:
    """Time that passes only when the runner sleeps, or when a test moves it on."""

    def __init__(self):
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


def test_a_batch_still_running_when_the_wait_runs_out():
    clock, batches = Clock(), FakeBatches(ends_after=99)
    run = AnthropicRunner("claude-opus-5-5", triage.Verdict, None, 8000, client=client(batches), poll_seconds=60,
                          wait_seconds=120, sleep=clock.sleep, clock=clock)
    with pytest.raises(BatchPending) as pending:
        run.run([Request("p00000", "prompt", "text")])
    assert pending.value.batch_id == "msgbatch_1" and batches.polls == 3


def test_the_wait_counts_from_the_start_of_the_step():
    clock, batches = Clock(), FakeBatches(ends_after=99)
    run = AnthropicRunner("claude-opus-5-5", triage.Verdict, None, 8000, client=client(batches), poll_seconds=60,
                          wait_seconds=600, sleep=clock.sleep, clock=clock)
    clock.now = 600  # fetching and screening the papers took the whole wait
    with pytest.raises(BatchPending):
        run.run([Request("p00000", "prompt", "text")])
    assert batches.created is not None and batches.polls == 1  # sent, looked at once, then left to be collected


def test_cost_at_list_and_batch_prices():
    usage = {"input_tokens": 1_000_000, "output_tokens": 100_000, "cache_read_input_tokens": 1_000_000}
    assert cost("claude-opus-5-5", usage, batch=False) == pytest.approx(4 + 2 + 0.2)
    assert cost("claude-opus-5-5", usage, batch=True) == pytest.approx(3.1)
    assert cost("some-other-model", usage, batch=True) is None


def test_abstracts_are_cleaned_and_asked_for_by_source():
    asked = []

    def answer(url):
        asked.append(url)
        return {"resultList": {"result": [{"abstractText": "<h4>Background</h4>Fibres &amp; terminals"}]}}

    assert europepmc.abstract("MED:8742308", answer) == "Background Fibres & terminals"
    assert "EXT_ID%3A8742308%20AND%20SRC%3AMED" in asked[0]
    assert europepmc.abstract("PPR:PPR1", lambda url: {"resultList": {"result": []}}) == ""
    with pytest.raises(ValueError):
        europepmc.abstract("8742308", answer)


def test_cli_reports_a_replayed_run(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(triage, "LEDGER", Ledger(tmp_path / "triage.csv", triage.LEDGER.columns))
    monkeypatch.setattr(cli, "read_manifest", lambda: PAPERS[:1])
    monkeypatch.setattr(triage.europepmc, "abstract", fetch)
    answers = tmp_path / "answers"
    answers.mkdir()
    (answers / f"{request_id('doi:10.1/a')}.json").write_text(
        '{"tests_connections": true, "evidence": [], "species": ["mouse"], "reason": "Traces."}')
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    assert cli.main(["triage", "--model", f"replay:{answers}"]) == 0
    assert "**triage** with replay:" in summary.read_text() and "- in: 1" in capsys.readouterr().out


def test_request_ids_are_stable_readable_and_unique():
    first = request_id("doi:10.1038/nature13186")
    assert first == request_id("doi:10.1038/nature13186") and first.startswith("doi_10_1038_nature13186-")
    assert request_id("doi:10.1/a") != request_id("doi:10.1_a")  # the same letters and digits, different keys
    long = request_id("doi:" + "9" * 200)
    assert len(long) <= 64 and re.fullmatch(r"[A-Za-z0-9_-]+", long)


class EarlierBatch(FakeBatches):
    """A batch sent by an earlier run, holding answers for the papers it was asked about."""

    def __init__(self, keys, ends_after=0):
        super().__init__(ends_after)
        self.keys = keys

    def create(self, requests):
        raise AssertionError("collecting must never send a new batch")

    def results(self, batch_id):
        good = '{"tests_connections": true, "evidence": ["retrograde_tracer"], "species": ["rat"], "reason": "Traces."}'
        for key in self.keys:
            yield SimpleNamespace(custom_id=request_id(key), result=SimpleNamespace(type="succeeded", message=message(good)))


def test_an_earlier_batch_is_collected_for_its_own_papers(tmp_path):
    ledger = Ledger(tmp_path / "triage.csv", triage.LEDGER.columns)
    batches = EarlierBatch(["doi:10.1/a"])
    run = AnthropicRunner("claude-opus-5-5", triage.Verdict, "low", 8000, client=client(batches), sleep=lambda s: None,
                          collect_batch="msgbatch_1")
    summary = triage.triage(PAPERS, run, limit=1, today="2026-10-08", ledger=ledger, abstract=fetch)
    rows = {r["key"]: r for r in ledger.read().values()}
    assert list(rows) == ["doi:10.1/a"] and rows["doi:10.1/a"]["verdict"] == "in"  # the limit doesn't hide its papers
    assert summary["papers"] == 1 and batches.created is None


def test_choose_limits_new_runs_and_follows_a_collected_batch():
    papers = [{"key": f"doi:10.1/{n}"} for n in range(5)]
    assert choose(papers, SimpleNamespace(), 2) == papers[:2]  # a runner that can't collect
    collecting = SimpleNamespace(known=lambda: {request_id("doi:10.1/3"), request_id("doi:10.1/4")})
    assert choose(papers, collecting, 1) == papers[3:]


def test_collecting_a_batch_still_running_sends_nothing():
    clock = Clock()
    run = AnthropicRunner("claude-opus-5-5", triage.Verdict, None, 8000, client=client(EarlierBatch([], ends_after=99)),
                          poll_seconds=60, wait_seconds=120, sleep=clock.sleep, clock=clock, collect_batch="msgbatch_1")
    with pytest.raises(BatchPending):
        run.known()


def test_the_latest_batch_is_collected_when_its_id_is_lost(tmp_path, capsys):
    from datetime import datetime, timezone

    batches = EarlierBatch(["doi:10.1/a"])
    batches.list = lambda limit: SimpleNamespace(data=[
        SimpleNamespace(id="msgbatch_old", created_at=datetime(2026, 10, 7, tzinfo=timezone.utc), processing_status="ended"),
        SimpleNamespace(id="msgbatch_new", created_at=datetime(2026, 10, 8, 21, 37, tzinfo=timezone.utc),
                        processing_status="in_progress")])
    asked = []
    retrieve = batches.retrieve
    batches.retrieve = lambda batch_id: asked.append(batch_id) or retrieve(batch_id)
    ledger = Ledger(tmp_path / "triage.csv", triage.LEDGER.columns)
    run = AnthropicRunner("claude-opus-5-5", triage.Verdict, "low", 8000, client=client(batches), sleep=lambda s: None,
                          collect_batch="latest")
    triage.triage(PAPERS, run, limit=1, today="2026-10-08", ledger=ledger, abstract=fetch)
    assert set(asked) == {"msgbatch_new"} and ledger.read()["doi:10.1/a"]["verdict"] == "in"
    assert "latest batch: msgbatch_new, sent 2026-10-08 21:37 UTC" in capsys.readouterr().out


def test_a_batch_of_another_steps_answers_is_refused():
    run = AnthropicRunner("claude-opus-5-5", extract.PaperClaims, "high", 8000, client=client(EarlierBatch(["doi:10.1/a"])),
                          sleep=lambda s: None, collect_batch="msgbatch_1")  # a triage batch, collected by extraction
    with pytest.raises(ValueError, match="another step's"):
        run.known()


def test_collect_needs_a_batch_id_and_the_batch_api():
    from pipeline.llm import runner

    with pytest.raises(ValueError, match="--collect"):
        runner("replay:answers", triage.Verdict, None, 8000, batch=True, collect_batch="msgbatch_1")
    with pytest.raises(ValueError, match="--collect"):
        runner("anthropic:claude-opus-5-5", triage.Verdict, None, 8000, batch=False, collect_batch="msgbatch_1")
    with pytest.raises(ValueError, match="--collect"):
        runner("anthropic:claude-opus-5-5", triage.Verdict, None, 8000, batch=True, collect_batch="; rm -rf /")
    assert runner("anthropic:claude-opus-5-5", triage.Verdict, None, 8000, batch=True, collect_batch="latest",
                  ).collect_batch == "latest"


def test_cli_tells_how_to_collect_a_batch_still_running(tmp_path, monkeypatch, capsys):
    def still_running(*args, **kwargs):
        raise BatchPending("msgbatch_7")

    monkeypatch.setattr(cli, "read_manifest", lambda: PAPERS[:1])
    monkeypatch.setattr(triage, "triage", still_running)
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    assert cli.main(["triage", "--model", "replay:answers"]) == 3
    assert "--collect msgbatch_7" in summary.read_text() and "--collect msgbatch_7" in capsys.readouterr().out


def test_a_paper_is_found_under_any_of_its_keys():
    paper = {"key": "doi:10.1/x", "doi": "10.1/x", "pmid": "77", "pmcid": "PMC9"}
    assert aliases(paper) == ["doi:10.1/x", "pubmed:77", "pmc:PMC9"]
    ledger = {"pubmed:77": {"key": "pubmed:77", "verdict": "in"}}  # triaged while it was keyed by its PubMed ID
    assert recorded(ledger, paper)["verdict"] == "in"
    assert [identifier(v) for v in ("10.1/X", "doi:10.1/x", "PMC9", "77")] == ["doi:10.1/x", "doi:10.1/x", "pmc:pmc9", "pubmed:77"]
    assert Redo(("PMC9",)).wants(paper, "triage@0.1.0", "triage@0.1.0") and Redo(("10.1/x, 5",)).wants(paper, None, "x")
    assert not Redo(("older",)).wants(paper, "triage@0.1.0", "triage@0.1.0") and Redo(("all",)).wants(paper, None, "x")


def test_only_answered_tries_count():
    paper = {"key": "doi:10.1/x"}
    for stop, due_after in (("expired", True), ("errored", True), ("refusal", False), ("max_tokens", False)):
        row = {"verdict": stop, "attempts": "0", "prompt": "p"}
        for _ in range(MAX_ATTEMPTS):
            row = {**row, "attempts": triage.row(paper, Result(None, stop), "abstract", "m", "p", "d", row)["attempts"]}
        assert due(paper, row, "verdict", triage.DECIDED, "p", Redo()) is due_after, stop
    assert not due(paper, {"verdict": "out", "attempts": "1", "prompt": "old"}, "verdict", triage.DECIDED, "new", Redo())


def test_results_waiting_on_another_branch_are_found(tmp_path):
    from pipeline import branches

    ledger = Ledger(tmp_path / "triage.csv", triage.LEDGER.columns)
    ledger.update([{"key": "doi:10.1/a", "verdict": "in", "attempts": "1", "date": "2026-10-08"}])
    header = ",".join(triage.LEDGER.columns)
    merged = f"{header}\ndoi:10.1/a,in,,,,,1,,,2026-10-08\n"  # its pull request merged: nothing new
    unmerged = merged + "doi:10.1/b,out,,,,,1,,,2026-10-09\n"

    def git(args, **kwargs):
        if "for-each-ref" in args:
            return SimpleNamespace(returncode=0, stdout="origin\norigin/main\norigin/literature/triage-1\norigin/literature/triage-2\n")
        shown = {"origin/main:triage.csv": merged, "origin/literature/triage-1:triage.csv": merged,
                 "origin/literature/triage-2:triage.csv": unmerged}.get(args[-1])
        return SimpleNamespace(returncode=0 if shown else 128, stdout=shown or "", stderr="")

    assert branches.waiting(ledger, run=git) == {"origin/literature/triage-2": 1}
    assert "origin/literature/triage-2 (1 paper(s))" in branches.refusal("triage", {"origin/literature/triage-2": 1})
    assert branches.waiting(ledger, run=lambda args, **kwargs: SimpleNamespace(returncode=128, stdout="", stderr="no")) == {}


def test_cli_refuses_while_another_branch_holds_results(tmp_path, monkeypatch, capsys):
    from pipeline import branches

    monkeypatch.setattr(cli, "read_manifest", lambda: PAPERS[:1])
    monkeypatch.setattr(cli, "branches", SimpleNamespace(waiting=lambda ledger: {"origin/literature/triage-2": 3},
                                                         refusal=branches.refusal))
    sent = []
    monkeypatch.setattr(triage, "triage", lambda *args, **kwargs: sent.append(args))
    assert cli.main(["triage", "--model", "replay:answers"]) == 1
    assert sent == [] and "pay for them twice" in capsys.readouterr().out
