"""Shared fixtures: a valid data tree built from the schema's examples, and replayed registry responses."""

import io
import json
import os
import shutil
from pathlib import Path
from urllib.parse import urlsplit

import pytest
import requests
import urllib3
import yaml
from requests.adapters import BaseAdapter
from requests.structures import CaseInsensitiveDict

from checks.http import Fetcher
from checks.identifiers import source_file_name

REPO = Path(__file__).resolve().parents[2]
EXAMPLES = REPO / "schema" / "examples" / "valid"
BROKEN = Path(__file__).parent / "fixtures" / "broken"
RECORDED = Path(__file__).parent / "fixtures" / "http" / "recorded.json"
RECORDING = os.environ.get("AXONARIUM_RECORD") == "1"


def default_opener(url, headers, timeout):
    """The network, for recording: status, headers and body of a GET."""
    response = requests.get(url, headers=headers, timeout=timeout)
    return response.status_code, dict(response.headers), response.content


class OpenerAdapter(BaseAdapter):
    """A requests transport that answers from an opener function, `(url, headers, timeout) -> (status, headers,
    body)`, instead of the network; an OSError it raises is a dropped connection."""

    def __init__(self, opener):
        super().__init__()
        self.opener = opener

    def send(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None):
        try:
            status, headers, body = self.opener(request.url, dict(request.headers), timeout)
        except OSError as error:
            raise requests.ConnectionError(error, request=request) from error
        response = requests.Response()
        response.status_code, response.url, response.request, response.reason = status, request.url, request, "Recorded"
        response.headers = CaseInsensitiveDict(headers)
        response.raw = urllib3.HTTPResponse(body=io.BytesIO(body), headers=headers, status=status, preload_content=False)
        response._content = body
        return response

    def close(self):
        pass


def _data_path(cls: str, record: dict) -> Path | None:
    """Where an example belongs in data/, following the layout in data/README.md."""
    if cls == "ConnectivityClaim":
        return Path("claims", "examples", f"{record['id']}.yaml")
    if cls == "HomologyClaim":
        return Path("homology", f"{record['id']}.yaml")
    if cls == "Atlas":
        return Path("entities", "atlases", f"{record['id']}.yaml")
    if cls == "Region":
        return Path("entities", "regions", f"{record['id'].replace(':', '_')}.yaml")
    if cls == "NeuronType":
        return Path("entities", "neuron_types", f"{record['id']}.yaml")
    if cls == "Source":
        return Path("sources", "doi", source_file_name(record["id"]))
    if cls == "Allowlist":
        return Path("allowlist.yaml")
    return None  # RetractionLog: the valid tree starts with an empty log


@pytest.fixture
def valid_tree(tmp_path) -> Path:
    data = tmp_path / "data"
    for example in sorted(EXAMPLES.glob("*.yaml")):
        cls = example.name.split("-", 1)[0]
        target = _data_path(cls, yaml.safe_load(example.read_text(encoding="utf-8")))
        if target:
            (data / target).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(example, data / target)
    (data / "retractions.yaml").write_text("entries: []\n", encoding="utf-8")
    return data


def overlay(data_dir: Path, fixture: Path) -> None:
    """Copy a broken fixture's files over the data tree."""
    shutil.copytree(fixture, data_dir, dirs_exist_ok=True)


def _keep(mapping: dict, keys: tuple[str, ...]) -> dict:
    return {k: mapping[k] for k in keys if k in mapping}


def trim(url: str, body):
    """A registry response cut down to the fields the checks read: small, and free of Allen content (ADR 0005)."""
    host = urlsplit(url).hostname
    if host == "www.ebi.ac.uk":
        terms = body.get("_embedded", {}).get("terms", [])
        return {"_embedded": {"terms": [_keep(t, ("obo_id", "is_obsolete", "term_replaced_by")) for t in terms]}}
    if host == "api.brain-map.org":
        return {"success": body.get("success"), "msg": [_keep(m, ("id", "graph_id")) for m in body.get("msg", [])]}
    if host == "api.crossref.org":
        return {"message": _keep(body["message"], ("DOI", "type", "subtype", "institution", "title", "container-title", "issued",
                                                   "license", "updated-by"))}
    if host == "api.datacite.org":
        attributes = _keep(body["data"]["attributes"], ("doi", "types", "titles", "publicationYear", "publisher", "container",
                                                        "rightsList"))
        return {"data": {"attributes": attributes}}
    if host == "eutils.ncbi.nlm.nih.gov" and "esearchresult" in body:
        return {"esearchresult": _keep(body["esearchresult"], ("count", "idlist", "ERROR"))}
    if host == "eutils.ncbi.nlm.nih.gov":
        result = body["result"]
        return {"result": {"uids": result["uids"], **{u: _keep(result[u], ("uid", "title", "articleids", "error", "pubdate", "source", "fulljournalname", "pubtype")) for u in result["uids"]}}}
    return body  # doi.org answers are already small


@pytest.fixture(scope="session")
def recordings():
    """Recorded registry responses by URL; with AXONARIUM_RECORD=1, re-recorded from the network and saved."""
    data = json.loads(RECORDED.read_text(encoding="utf-8")) if RECORDED.exists() else {}
    yield data
    if RECORDING:
        RECORDED.parent.mkdir(parents=True, exist_ok=True)
        RECORDED.write_text(json.dumps(dict(sorted(data.items())), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


_fresh: set[str] = set()


@pytest.fixture
def replay(recordings):
    """An opener that answers from the recordings and fails the test on any URL it has none for."""
    def opener(url, headers, timeout):
        if RECORDING and url not in _fresh:
            status, _, body = default_opener(url, headers, timeout)
            recordings[url] = {"status": status, "body": trim(url, json.loads(body)) if status == 200 else None}
            _fresh.add(url)
        if url not in recordings:
            pytest.fail(f"no recorded response for {url}; run the tests with AXONARIUM_RECORD=1")
        entry = recordings[url]
        return entry["status"], {}, json.dumps(entry["body"]).encode() if entry["body"] is not None else b""
    return opener


@pytest.fixture
def fetch(replay) -> Fetcher:
    return Fetcher(None, OpenerAdapter(replay))
