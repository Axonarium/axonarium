"""The gold curation tool (sprint 0.5a): the paper, region search and drafts in the gold format, locally."""

import json
import threading
from http.client import HTTPConnection
from pathlib import Path

import pytest
import yaml

from curate.server import Curation, ThreadingHTTPServer, handler
from evals.harness import gold
from pipeline.extract import Lexicon
from pipeline.tests.test_extract import LEXICON

ARTICLE = (Path(__file__).parents[2] / "pipeline" / "tests" / "fixtures" / "article.xml").read_bytes()
MOUSE, RAT = "NCBITaxon:10090", "NCBITaxon:10116"
MANIFEST = [{"key": "doi:10.1/a", "doi": "10.1/a", "pmid": "1", "pmcid": "PMC1", "title": "BLA outputs"}]


def claim(subject="MBA:295", target="MBA:536", species=MOUSE, **fields):
    return {"subject": {"type": "region", "id": subject}, "predicate": "projects_to", "object": {"type": "region", "id": target},
            "species": species, "evidence_class": "anterograde_tracer", "result": "present", "sign": "unknown",
            "locator": "Fig. 1"} | fields


@pytest.fixture
def curation(tmp_path):
    return Curation(Lexicon(LEXICON["atlases"], LEXICON["neuron_types"]), tmp_path / "drafts", MANIFEST, fetch=lambda pmcid: ARTICLE)


def test_the_whole_paper_with_its_identifiers(curation):
    paper = curation.paper("PMC1")
    assert paper["source"] == {"doi": "10.1/a", "pmid": "1", "pmcid": "PMC1"} and paper["title"] == "BLA outputs"
    texts = [b["text"] for b in paper["blocks"]]
    assert "INTRO: earlier work showed many things." in texts and "DISCUSSION: this agrees with earlier work." in texts
    assert {"text": "Results", "heading": True} in paper["blocks"]
    with pytest.raises(ValueError):
        curation.paper("12345")


def test_region_search_by_species(curation):
    assert [r["id"] for r in curation.regions("bla", MOUSE)][:1] == ["MBA:295"]
    assert curation.regions("bla", MOUSE)[0]["exact"] is True
    assert [r["id"] for r in curation.regions("basolateral", RAT)] == ["UBERON:0002887"]  # rats: the mapped UBERON term
    assert [r["id"] for r in curation.regions("glutamatergic", MOUSE)] == ["nt-3kvfdzf7wn"]
    assert curation.regions("glutamatergic", RAT) == [] and curation.regions("  ", MOUSE) == []


def test_drafts_are_saved_in_the_gold_format_after_checks(curation, tmp_path):
    path = curation.save({"name": "bla-outputs", "source": {"doi": "10.1/a", "pmcid": "PMC1"},
                          "claims": [claim(), claim(target="MBA:672", result="absent", locator="Fig. 2")]})
    saved = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert saved["text"] == {"europe_pmc": "PMC1"} and len(saved["claims"]) == 2
    (tmp_path / "drafts" / "gold.yaml").write_text("version: draft\nfrozen: null\n", encoding="utf-8")
    loaded = gold.load(tmp_path / "drafts")  # the eval harness reads it as a gold set
    assert loaded.papers[0].claims[1].result == "absent"
    assert curation.load("bla-outputs")["claims"][0]["subject"]["id"] == "MBA:295" and curation.drafts() == ["bla-outputs"]

    with pytest.raises(ValueError, match="name"):
        curation.save({"name": "../escape", "source": {"doi": "10.1/a"}, "claims": []})
    with pytest.raises(ValueError, match="not in the region lexicon"):
        curation.save({"name": "x", "source": {"doi": "10.1/a"}, "claims": [claim(target="MBA:999")]})
    with pytest.raises(ValueError, match="claim 1"):
        curation.save({"name": "x", "source": {"doi": "10.1/a"}, "claims": [claim(result="maybe")]})
    with pytest.raises(ValueError, match="source"):
        curation.save({"name": "x", "source": {}, "claims": []})


def test_the_server_answers_locally_and_takes_only_json(curation):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler(curation))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        def ask(method, path, body=None, kind="application/json"):
            connection = HTTPConnection("127.0.0.1", server.server_address[1])
            connection.request(method, path, body=body, headers={"Content-Type": kind} if body is not None else {})
            response = connection.getresponse()
            return response.status, response.read(), response.getheader("Content-Security-Policy")

        status, page, policy = ask("GET", "/")
        assert status == 200 and b"Gold curation" in page and "default-src 'self'" in policy
        assert json.loads(ask("GET", "/api/regions?q=cea&species=NCBITaxon:10090")[1])[0]["id"] == "MBA:536"
        assert json.loads(ask("GET", "/api/enums")[1])["evidence_for"]["synapses_onto"] == ["electron_microscopy", "transsynaptic_tracer"]
        draft = json.dumps({"name": "via-http", "source": {"pmcid": "PMC1"}, "claims": [claim()]})
        assert ask("POST", "/api/save", draft, kind="text/plain")[0] == 400  # what a form on another site could send
        assert ask("POST", "/api/save", draft)[0] == 200
        assert ask("GET", "/api/paper?pmcid=nope")[0] == 400
    finally:
        server.shutdown()
