"""Triage (sprint 2.2a): abstracts in, verdicts in corpus/triage.csv out; never twice for the same prompt."""

import csv
from types import SimpleNamespace

import pytest

from pipeline import cli, europepmc, triage
from pipeline.corpus import Ledger
from pipeline.llm import AnthropicRunner, BatchPending, Request, Result, cost, parse

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
                                       "species": "mouse", "reason": "Traces BLA outputs with AAV.", "model": "claude-opus-5-5",
                                       "prompt": "triage@0.1.0", "date": "2026-10-08"}
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


def test_limit_and_a_new_prompt_version(tmp_path):
    ledger = Ledger(tmp_path / "triage.csv", triage.LEDGER.columns)
    triage.triage(PAPERS, FakeRun(), limit=1, today="2026-10-08", ledger=ledger, abstract=fetch)
    assert list(ledger.read()) == ["doi:10.1/b"]
    prompt = tmp_path / "triage.md"
    prompt.write_text(triage.PROMPT.read_text(encoding="utf-8").replace("triage@0.1.0", "triage@0.2.0"), encoding="utf-8")
    run = FakeRun()
    triage.triage(PAPERS[:2], run, limit=10, today="2026-10-09", ledger=ledger, abstract=fetch, prompt=prompt)
    assert len(run.sent) == 2 and ledger.read()["doi:10.1/b"]["prompt"] == "triage@0.2.0"


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


def test_a_batch_still_running_when_the_wait_runs_out():
    run = AnthropicRunner("claude-opus-5-5", triage.Verdict, None, 8000, client=client(FakeBatches(ends_after=99)),
                          poll_seconds=60, wait_seconds=120, sleep=lambda s: None)
    with pytest.raises(BatchPending) as pending:
        run.run([Request("p00000", "prompt", "text")])
    assert pending.value.batch_id == "msgbatch_1"


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
    (answers / "p00000.json").write_text('{"tests_connections": true, "evidence": [], "species": ["mouse"], "reason": "Traces."}')
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    assert cli.main(["triage", "--model", f"replay:{answers}"]) == 0
    assert "**triage** with replay:" in summary.read_text() and "cost: unknown for this model" in capsys.readouterr().out
