"""The MCP tools, called through the MCP protocol in-process, against canned read-API answers."""

import json
from urllib.parse import unquote

import anyio
import httpx
from mcp import Client

from axonarium_mcp.server import create

BLA = {"id": "MBA:295", "acronym": "BLA", "name": "Basolateral amygdalar nucleus", "atlas": "allen-mouse-ccf-2017",
       "parent": "MBA:703", "uberon": "UBERON:0006107", "uberon_label": None, "amygdala": True}
EDGE = "MBA:295|projects_to|MBA:672|NCBITaxon:10090"
ALLEN = {"id": "allen-institute", "name": "Allen Institute terms of use", "url": "https://alleninstitute.org/terms-of-use/",
         "note": "Non-commercial use with attribution."}
CLAIM = {"id": "clm-a", "subject": {"type": "region", "id": "MBA:295", "atlas": None}, "predicate": "projects_to",
         "object": {"type": "region", "id": "MBA:672", "atlas": None}, "species": "NCBITaxon:10090",
         "evidence_class": "anterograde_tracer", "result": "present", "sign": "unknown", "strength": None,
         "measurements": [{"quantity": "projection_density", "value": 0.42, "unit": "1"}],
         "citation": {"source": "doi:10.1038/nature13186", "doi": "10.1038/nature13186", "pmid": None, "pmcid": None,
                      "arxiv": None, "locator": "Allen Mouse Brain Connectivity Atlas, experiment 1"},
         "paraphrase": "Tracer injected into BLA labelled axons in CP.", "excerpt": None, "curation": {},
         "verification": None, "status": "accepted", "extra": None, "terms": ALLEN}


def link(region, density):
    return {"connection": f"MBA:295|projects_to|{region}|NCBITaxon:10090", "region": {"id": region, "acronym": None, "name": None},
            "density": density, "claims": 1, "accepted": 1}


def api(request: httpx.Request) -> httpx.Response:
    path = unquote(request.url.path)
    if path == "/api/v1/regions":
        assert request.url.params["q"] == "basolateral"
        return httpx.Response(200, json={"items": [BLA], "limit": 10, "offset": 0, "total": 1})
    if path == "/api/v1/regions/MBA:295":
        return httpx.Response(200, json={"region": BLA, "subregions": [], "inputs": [link("MBA:31", 0.2)],
                                         "outputs": [link("MBA:672", 0.42), link("MBA:56", 0.05)]})
    if path == "/api/v1/connections":
        return httpx.Response(200, json={"items": [], "limit": 20, "offset": 0, "total": 0})
    if path == f"/api/v1/connections/{EDGE}":
        assert "%7C" in request.url.raw_path.decode()  # the ID is one encoded path segment
        return httpx.Response(200, json={"id": EDGE, "subject": {"id": "MBA:295", "acronym": "BLA", "name": "Basolateral amygdalar nucleus"},
                                         "predicate": "projects_to", "object": {"id": "MBA:672", "acronym": "CP", "name": "Caudoputamen"},
                                         "species": "NCBITaxon:10090", "claims": 1, "present": 1, "absent": 0, "density": 0.42,
                                         "evidence_classes": ["anterograde_tracer"], "terms": ["allen-institute"], "claims_detail": [CLAIM]})
    return httpx.Response(404, json={"error": f"No region {path.rsplit('/', 1)[-1]}"})


def call(tool, arguments):
    server = create(httpx.Client(base_url="https://axonarium.test/api/v1", transport=httpx.MockTransport(api)))

    async def run():
        async with Client(server) as client:
            return await client.call_tool(tool, arguments)
    return anyio.run(run)


def result(tool, arguments):
    answer = call(tool, arguments)
    assert not answer.is_error, answer.content
    return answer.structured_content if answer.structured_content is not None else json.loads(answer.content[0].text)


def test_tools_are_listed_and_read_only():
    server = create(httpx.Client(transport=httpx.MockTransport(api)))

    async def run():
        async with Client(server) as client:
            return (await client.list_tools()).tools
    tools = {tool.name: tool for tool in anyio.run(run)}
    assert set(tools) == {"search_regions", "region_connections", "find_connections", "connection_evidence"}
    assert all(tool.annotations and tool.annotations.read_only_hint for tool in tools.values())


def test_search_regions():
    found = result("search_regions", {"query": "basolateral"})
    assert found["regions"][0]["id"] == "MBA:295"


def test_region_connections_by_direction_and_density():
    found = result("region_connections", {"region_id": "MBA:295", "direction": "outputs", "min_density": 0.1})
    assert [c["region"]["id"] for c in found["connections"]] == ["MBA:672"] and found["total"] == 2
    assert result("region_connections", {"region_id": "MBA:295", "direction": "inputs"})["connections"][0]["region"]["id"] == "MBA:31"


def test_connection_evidence_cites_and_states_terms():
    found = result("connection_evidence", {"connection_id": EDGE})
    claim = found["claims"][0]
    assert claim["citation"]["url"] == "https://doi.org/10.1038/nature13186"
    assert claim["citation"]["locator"] == "Allen Mouse Brain Connectivity Atlas, experiment 1"
    assert claim["terms"] == "Allen Institute terms of use: Non-commercial use with attribution."
    assert claim["projection_density"] == 0.42 and claim["status"] == "accepted"


def test_unknown_ids_are_tool_errors():
    answer = call("region_connections", {"region_id": "MBA:999999"})
    assert answer.is_error and "No region" in answer.content[0].text
