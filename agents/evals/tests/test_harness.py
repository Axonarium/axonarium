"""The eval harness: gold sets, scoring, providers (with stand-in clients, no network) and reports."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from pydantic import TypeAdapter, ValidationError

from evals.harness import gold as goldsets
from evals.harness import providers
from evals.harness.models import SCHEMA, GoldClaim, values
from evals.harness.prompts import read_prompt
from evals.harness.run import AGENTS, main, markdown, run
from evals.harness.score import score_paper
from pipeline import extract
from pipeline.corpus import Ledger
from pipeline.extract import Draft, PaperClaims
from pipeline.llm import Result

PLACEHOLDER = AGENTS / "evals" / "fixtures" / "placeholder"
EXTRACTOR = AGENTS / "roles" / "extractor.md"
ARTICLE = AGENTS / "pipeline" / "tests" / "fixtures" / "article.xml"  # a JATS paper with every kind of section
MOUSE, RAT = "NCBITaxon:10090", "NCBITaxon:10116"
CLEAN = lambda paragraphs: [0.0] * len(paragraphs)  # noqa: E731  a stand-in classifier that flags nothing
LEXICON = {
    "atlases": {"allen-mouse-ccf-2017": {"species": MOUSE, "regions": [
        {"id": "MBA:295", "acronym": "BLA", "name": "Basolateral amygdalar nucleus", "uberon": "UBERON:0002887", "amygdala": True},
        {"id": "MBA:536", "acronym": "CEA", "name": "Central amygdalar nucleus", "uberon": "UBERON:0002883", "amygdala": True},
    ]}},
    "neuron_types": [{"id": "nt-3kvfdzf7wn", "name": "MEA glutamatergic neurons", "species": MOUSE, "region": "MBA:403"}],
}


def lexicon() -> extract.Lexicon:
    return extract.Lexicon(LEXICON["atlases"], LEXICON["neuron_types"])


def draft(subject, obj, species=MOUSE, predicate="projects_to", evidence="anterograde_tracer", result="present", sign="unknown"):
    entity = lambda i: {"type": "region", "id": i, "name_in_paper": i}  # noqa: E731
    return Draft.model_validate({"subject": entity(subject), "predicate": predicate, "object": entity(obj), "species": species,
                                 "evidence_class": evidence, "result": result, "sign": sign, "locator": "Fig. 1", "paraphrase": "p",
                                 "strength": None, "measurements": []})


def gold(subject, obj, **kwargs):
    claim = draft(subject, obj, **kwargs).model_dump()
    for side in ("subject", "object"):
        del claim[side]["name_in_paper"]
    for name in ("paraphrase", "strength", "measurements"):
        del claim[name]
    return GoldClaim.model_validate(claim)


# Models

def test_enumerations_follow_the_schema():
    schema = yaml.safe_load(SCHEMA.read_text(encoding="utf-8"))
    assert values("EvidenceClass") == tuple(schema["enums"]["EvidenceClass"]["permissible_values"])
    with pytest.raises(ValidationError):
        draft("MBA:295", "MBA:536", evidence="hearsay")


def test_the_pipelines_output_model_becomes_a_structured_output_schema():
    from anthropic.lib._parse._transform import transform_schema  # what messages.stream(output_format=…) applies

    schema = transform_schema(TypeAdapter(PaperClaims).json_schema())
    assert schema["type"] == "object" and schema["additionalProperties"] is False and schema["required"] == ["claims"]


# Gold sets

def test_the_placeholder_gold_set_loads():
    found = goldsets.load(PLACEHOLDER)
    assert found.version == "placeholder" and [p.name for p in found.papers] == ["synthetic-physiology", "synthetic-tracing"]
    assert sum(len(p.claims) for p in found.papers) == 6
    assert "PHA-L" in goldsets.text(found, found.papers[1], CLEAN).text


def test_unknown_keys_in_a_gold_paper_are_refused(tmp_path):
    (tmp_path / "papers").mkdir()
    (tmp_path / "gold.yaml").write_text("version: x\n", encoding="utf-8")
    (tmp_path / "papers" / "p.yaml").write_text("source: {}\ntext: {file: t}\nclaims: []\nnotes: x\n", encoding="utf-8")
    with pytest.raises(ValueError, match="notes"):
        goldsets.load(tmp_path)


def test_open_access_text_is_fetched_once_and_cached(tmp_path):
    xml = (b"<article><front><article-title>A <i>title</i></article-title><abstract><p>Short  abstract.</p></abstract></front>"
           b"<body><sec><title>Results</title><p>BLA projects to CeA.</p></sec></body></article>")
    asked = []
    paper = goldsets.Paper("p", {}, {"europe_pmc": "PMC1"}, [])
    found = goldsets.GoldSet(tmp_path, "x", None, [paper])
    download = lambda url: asked.append(url) or xml  # noqa: E731
    first = goldsets.text(found, paper, CLEAN, download=download, cache=tmp_path / "cache")
    assert first.text == "A title\nShort abstract.\nResults\nBLA projects to CeA." and not first.flagged
    assert goldsets.text(found, paper, CLEAN, download=download, cache=tmp_path / "cache") == first
    assert asked == ["https://www.ebi.ac.uk/europepmc/webservices/rest/PMC1/fullTextXML"]
    assert (tmp_path / "cache" / "PMC1.xml").read_bytes() == xml


def test_committed_jats_is_screened(tmp_path):
    (tmp_path / "a.xml").write_bytes(b'<article><body><p>Seen.<styled-content style="color:#fff">Unseen.</styled-content>'
                                     b'</p></body></article>')
    paper = goldsets.Paper("p", {}, {"jats": "a.xml"}, [])
    screened = goldsets.text(goldsets.GoldSet(tmp_path, "x", None, [paper]), paper, CLEAN)
    assert screened.text == "Seen." and [f.layer for f in screened.findings] == ["hidden-markup"]


def test_jats_is_cut_to_what_holds_claims_as_the_pipeline_cuts_it(tmp_path):
    (tmp_path / "a.xml").write_bytes(ARTICLE.read_bytes())
    paper = goldsets.Paper("p", {}, {"jats": "a.xml"}, [])
    kept = goldsets.text(goldsets.GoldSet(tmp_path, "x", None, [paper]), paper, CLEAN).text
    assert "RESULTS" in kept and "CAPTION ONE" in kept
    assert "INTRO" not in kept and "DISCUSSION" not in kept and "REFERENCE" not in kept


# Scoring

def test_a_perfect_answer_scores_one():
    claims = [gold("MBA:295", "MBA:536"), gold("MBA:295", "MBA:972", result="absent")]
    tally = score_paper(claims, [draft("MBA:295", "MBA:536"), draft("MBA:295", "MBA:972", result="absent")]).metrics()
    assert (tally["precision"], tally["recall"], tally["f1"], tally["absent_recall"]) == (1.0, 1.0, 1.0, 1.0)
    assert set(tally["field_accuracy"].values()) == {1.0}


def test_reversed_and_wrong_species_claims_are_counted():
    claims = [gold("MBA:295", "MBA:536"), gold("UBERON:0002886", "UBERON:0002883", species=RAT)]
    predicted = [draft("MBA:536", "MBA:295"), draft("UBERON:0002886", "UBERON:0002883", species=MOUSE)]
    counts = score_paper(claims, predicted).metrics()["counts"]
    assert counts == {"predicted": 2, "gold": 2, "matched": 0, "direction_errors": 1, "species_errors": 1}


def test_fields_are_scored_on_matched_claims_and_any_shown_method_counts():
    claims = [gold("MBA:295", "MBA:536"), gold("MBA:295", "MBA:536", evidence="retrograde_tracer"),
              gold("UBERON:0002884", "UBERON:0002883", species=RAT, predicate="functionally_connects_to",
                   evidence="paired_recording", sign="inhibitory")]
    predicted = [draft("MBA:295", "MBA:536", evidence="retrograde_tracer"),
                 draft("UBERON:0002884", "UBERON:0002883", species=RAT, predicate="functionally_connects_to",
                       evidence="paired_recording", sign="excitatory")]
    metrics = score_paper(claims, predicted).metrics()
    assert metrics["counts"]["gold"] == 2 and metrics["recall"] == 1.0  # the two methods are one connection
    assert metrics["field_accuracy"] == {"evidence_class": 1.0, "result": 1.0, "sign": 0.5}


def test_nothing_predicted():
    metrics = score_paper([gold("MBA:295", "MBA:536")], []).metrics()
    assert (metrics["precision"], metrics["recall"], metrics["f1"]) == (None, 0.0, None)


# Providers, with stand-in clients

class Stream:
    def __init__(self, message):
        self.message = message

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get_final_message(self):
        if isinstance(self.message, Exception):
            raise self.message
        return self.message


def anthropic_client(message, calls):
    def stream(**kwargs):
        calls.append(kwargs)
        return Stream(message)
    return SimpleNamespace(messages=SimpleNamespace(stream=stream))


def message(stop="end_turn", parsed=None, details=None):
    return SimpleNamespace(stop_reason=stop, parsed_output=parsed, stop_details=details,
                           usage=SimpleNamespace(input_tokens=1000, output_tokens=200))


ANSWER = PaperClaims(claims=[draft("MBA:295", "MBA:536")])


def test_anthropic_asks_for_structured_output_with_the_effort_and_no_fallback():
    calls = []
    model = providers.AnthropicProvider("claude-opus-5-5", "high", client=anthropic_client(message(parsed=ANSWER), calls))
    answer = model.extract("p", "the prompt", "the paper")
    assert answer.extraction == ANSWER and answer.stop == "end_turn" and answer.usage == {"input_tokens": 1000, "output_tokens": 200}
    [call] = calls
    assert call["model"] == "claude-opus-5-5" and call["system"] == "the prompt" and call["output_format"] is PaperClaims
    assert call["messages"] == [{"role": "user", "content": "the paper"}] and call["output_config"] == {"effort": "high"}
    assert "fallbacks" not in call and "thinking" not in call and model.name == "anthropic:claude-opus-5-5"


def test_anthropic_without_effort_leaves_it_unset():
    calls = []
    providers.AnthropicProvider("claude-haiku-4-5", None, client=anthropic_client(message(parsed=ANSWER), calls)).extract("p", "s", "t")
    assert "output_config" not in calls[0]


@pytest.mark.parametrize("reply,stop,detail", [
    (message("refusal", details=SimpleNamespace(category="bio")), "refusal", "bio"),
    (message("max_tokens"), "max_tokens", None),
    (ValueError("Unterminated string"), "invalid", "Unterminated string"),
])
def test_anthropic_failures_are_recorded_not_scored(reply, stop, detail):
    answer = providers.AnthropicProvider("m", client=anthropic_client(reply, [])).extract("p", "s", "t")
    assert answer.extraction is None and answer.stop == stop and answer.detail == detail


def test_openai_asks_for_structured_output_with_the_effort():
    calls = []

    def parse(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(output_parsed=ANSWER, status="completed", usage=SimpleNamespace(input_tokens=5, output_tokens=7))

    model = providers.OpenAIProvider("a-model", "high", client=SimpleNamespace(responses=SimpleNamespace(parse=parse)))
    answer = model.extract("p", "the prompt", "the paper")
    assert answer.extraction == ANSWER and answer.usage == {"input_tokens": 5, "output_tokens": 7}
    assert calls == [{"model": "a-model", "instructions": "the prompt", "input": "the paper", "text_format": PaperClaims,
                      "reasoning": {"effort": "high"}}]


def test_replay_reads_saved_answers(tmp_path):
    (tmp_path / "p.json").write_text(ANSWER.model_dump_json(), encoding="utf-8")
    (tmp_path / "bad.json").write_text('{"claims": [{"subject": 1}]}', encoding="utf-8")
    replay = providers.ReplayProvider(str(tmp_path))
    assert replay.extract("p", "s", "t").extraction == ANSWER
    assert replay.extract("bad", "s", "t").stop == "invalid" and replay.extract("missing", "s", "t").stop == "error"


@pytest.mark.parametrize("spec", ["claude-opus-5-5", "mystery:model"])
def test_provider_specs_are_checked(spec):
    with pytest.raises(ValueError):
        providers.provider(spec)


# Runs and reports

def test_the_projects_prompts_are_versioned():
    for prompt in (AGENTS / "roles").glob("*.md"):
        prompt_id, text = read_prompt(prompt)  # refuses a prompt without a versioned id
        assert prompt_id and text


def test_a_prompt_without_a_version_is_refused(tmp_path):
    (tmp_path / "p.md").write_text("Extract claims.\n", encoding="utf-8")
    with pytest.raises(ValueError, match="front matter"):
        read_prompt(tmp_path / "p.md")


def test_a_run_scores_every_paper_and_keeps_failures():
    class OneFails:
        name = "test:model"

        def extract(self, paper, system, text):
            if paper == "synthetic-tracing":
                return providers.Answer(None, "refusal", {"input_tokens": 3, "output_tokens": 0})
            return providers.Answer(PaperClaims(claims=[draft("UBERON:0002886", "UBERON:0002883", species=RAT,
                                                             predicate="functionally_connects_to",
                                                             evidence="optogenetic_circuit_mapping", sign="excitatory")]),
                                    "end_turn", {"input_tokens": 10, "output_tokens": 4})

    result = run(goldsets.load(PLACEHOLDER), OneFails(), EXTRACTOR, lexicon(), "high", "2026-10-04",
                 lambda g, paper: goldsets.text(g, paper, CLEAN))
    assert result["failures"] == {"synthetic-tracing": "refusal"} and result["usage"] == {"input_tokens": 13, "output_tokens": 4}
    assert result["counts"]["gold"] == 6 and result["counts"]["matched"] == 1 and result["precision"] == 1.0
    assert result["screened"] == []


def test_a_flagged_paper_is_never_sent_to_the_model():
    class Refuses:
        name = "test:model"

        def extract(self, paper, system, text):
            raise AssertionError(f"{paper} reached the model")

    flags_everything = lambda paragraphs: [1.0] * len(paragraphs)  # noqa: E731
    result = run(goldsets.load(PLACEHOLDER), Refuses(), EXTRACTOR, lexicon(), "high", "2026-10-04",
                 lambda g, paper: goldsets.text(g, paper, flags_everything))
    assert result["screened"] == ["synthetic-physiology", "synthetic-tracing"] and result["recall"] == 0.0
    assert result["papers"][0]["screen"][0]["layer"] == "injection"
    assert "**synthetic-tracing** was flagged by the hidden-text screen" in markdown(result)


def lexicon_file(tmp_path) -> Path:
    path = tmp_path / "lexicon.json"
    path.write_text(json.dumps(LEXICON), encoding="utf-8")
    return path


def test_cli_writes_the_report(tmp_path, capsys):
    out = tmp_path / "results"
    answers = PLACEHOLDER / "answers"
    assert main(["--gold", str(PLACEHOLDER), "--model", f"replay:{answers}", "--lexicon", str(lexicon_file(tmp_path)),
                 "--out", str(out)],
                classify=lambda paragraphs: [0.99 if "previous instructions" in p.lower() else 0.0 for p in paragraphs]) == 0
    [report] = list(out.glob("*.json"))
    result = json.loads(report.read_text(encoding="utf-8"))
    assert (result["precision"], result["counts"]["direction_errors"], result["absent_recall"]) == (0.8, 1, 0.0)
    assert result["field_accuracy"]["sign"] == 0.75 and Path(str(report).removesuffix(".json") + ".md").exists()
    assert "precision 80.0%, recall 66.7%" in capsys.readouterr().out
    # The report says which lexicon and text the model read, so scores from before sprint 0.6a can be told apart.
    about = result["lexicon"]
    assert about["path"] == str(tmp_path / "lexicon.json") and len(about["sha256"]) == 64 and about["date"][:2] == "20"
    assert result["text"].startswith("JATS cut to the title, abstract, methods, results and captions")
    summary = Path(str(report).removesuffix(".json") + ".md").read_text(encoding="utf-8")
    assert f"Lexicon of {about['date']} (sha256 {about['sha256'][:12]}). JATS cut to" in summary


def test_cli_stops_without_a_lexicon(tmp_path, capsys):
    answers = PLACEHOLDER / "answers"
    assert main(["--gold", str(PLACEHOLDER), "--model", f"replay:{answers}", "--lexicon", str(tmp_path / "none.json"),
                 "--out", str(tmp_path / "results")], classify=CLEAN) == 1
    assert "no lexicon at" in capsys.readouterr().out and not (tmp_path / "results").exists()


def test_cli_stops_when_the_screen_misses_a_planted_fixture(tmp_path, capsys):
    answers = PLACEHOLDER / "answers"
    assert main(["--gold", str(PLACEHOLDER), "--model", f"replay:{answers}", "--lexicon", str(lexicon_file(tmp_path)),
                 "--out", str(tmp_path)], classify=CLEAN) == 1
    assert "the hidden-text screen fails its fixtures: planted-visible-instruction.xml: missed" in capsys.readouterr().out
    assert [p.name for p in tmp_path.iterdir()] == ["lexicon.json"]


def test_cli_reports_a_bad_model_spec(capsys):
    assert main(["--gold", str(PLACEHOLDER), "--model", "nope"]) == 1
    assert "provider:model" in capsys.readouterr().out


# Parity with the pipeline (sprint 0.6a)

def test_a_harness_run_sends_the_model_what_the_pipeline_sends(tmp_path):
    """The same open-access paper, through the harness and through the pipeline's extraction, reaches the model as the
    same instructions (the extractor prompt and the region lexicon) and the same pruned, screened text."""
    article = ARTICLE.read_bytes()
    (tmp_path / "gold" / "papers").mkdir(parents=True)
    (tmp_path / "gold" / "gold.yaml").write_text("version: parity\n", encoding="utf-8")
    (tmp_path / "gold" / "papers" / "p.yaml").write_text("source: {pmcid: PMC1}\ntext: {europe_pmc: PMC1}\nclaims: []\n",
                                                         encoding="utf-8")

    class Harness:
        name = "test:model"

        def __init__(self):
            self.sent = []

        def extract(self, paper, system, text):
            self.sent.append((system, text))
            return providers.Answer(PaperClaims(claims=[]), "end_turn")

    harness = Harness()
    run(goldsets.load(tmp_path / "gold"), harness, EXTRACTOR, lexicon(), "high", "2026-10-14",
        lambda g, paper: goldsets.text(g, paper, CLEAN, download=lambda url: article, cache=tmp_path / "cache"))

    class Pipeline:
        model, name, batch = "test-model", "test:model", False

        def __init__(self):
            self.sent = []

        def run(self, requests):
            self.sent += requests
            return {r.id: Result(PaperClaims(claims=[]), "end_turn") for r in requests}

    pipeline = Pipeline()
    paper = {"key": "doi:10.1/a", "doi": "10.1/a", "pmid": "1", "pmcid": "PMC1", "full_text": "true", "open_access": "true"}
    extract.extract([paper], pipeline, 1, lexicon(), CLEAN, today="2026-10-14",
                    ledger=Ledger(tmp_path / "extracted.csv", extract.LEDGER.columns), triaged={paper["key"]: {"verdict": "in"}},
                    claims_dir=tmp_path / "claims", text=lambda p: extract.full_text(p, CLEAN, fetch=lambda pmcid: article))

    [(system, text)] = harness.sent
    [request] = pipeline.sent
    assert system == request.system and text == request.text
    assert "## Region lexicon" in system and "MBA:295 | BLA | Basolateral amygdalar nucleus | UBERON:0002887" in system
    assert "RESULTS" in text and "DISCUSSION" not in text
