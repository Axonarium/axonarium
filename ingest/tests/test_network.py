"""The build's HTTP goes through one retried, rate-limited session that can cache (ADR 0012)."""

import json

from checks.tests.conftest import OpenerAdapter
from ingest.network import loaders

OLS_ANSWER = {"_embedded": {"terms": [{"obo_id": "UBERON:0002887", "label": "basal amygdaloid nucleus"}]},
              "page": {"totalPages": 1}}
OLS_ROOT = {"label": "amygdala"}


def opener_for(asked):
    def opener(url, headers, timeout):
        asked.append(url)
        if "ols4" in url:
            return 200, {}, json.dumps(OLS_ANSWER if "hierarchicalDescendants" in url else OLS_ROOT).encode()
        if "api.brain-map.org" in url:
            return 200, {}, json.dumps({"success": True, "msg": []}).encode()
        raise AssertionError(f"unexpected request {url}")
    return opener


def test_loaders_use_the_session_and_its_cache(tmp_path):
    asked = []
    terms, _, connectivity = loaders(tmp_path, OpenerAdapter(opener_for(asked)))
    assert terms(["UBERON:0001876"])["UBERON:0001876"] == {"UBERON:0001876": "amygdala", "UBERON:0002887": "basal amygdaloid nucleus"}
    assert connectivity("allen-mouse-ccf-2017", [295], {295: "BLA"}) == []
    assert any("api.brain-map.org" in url and "start_row=0" in url for url in asked)
    before = len(asked)
    again, _, _ = loaders(tmp_path, OpenerAdapter(opener_for(asked)))
    assert again(["UBERON:0001876"])["UBERON:0001876"]["UBERON:0002887"] == "basal amygdaloid nucleus"
    assert len(asked) == before  # answered from the cache


def test_without_a_cache_folder_every_run_asks(tmp_path):
    asked = []
    loaders(None, OpenerAdapter(opener_for(asked)))[0](["UBERON:0001876"])
    loaders(None, OpenerAdapter(opener_for(asked)))[0](["UBERON:0001876"])
    assert len(asked) == 4  # the root's label and its descendants, each run
