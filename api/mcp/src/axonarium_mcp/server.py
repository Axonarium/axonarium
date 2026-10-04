"""Axonarium's MCP server: tools that answer brain-connectivity questions from the read API, with citations.

The tools only read https://axonarium.com/api/v1 (ADR 0013); set AXONARIUM_API to point at another deployment.
Run it with `uvx --from "git+https://github.com/axonarium/axonarium#subdirectory=api/mcp" axonarium-mcp`.
"""

import logging
import os
from typing import Any, Literal
from urllib.parse import quote

import httpx
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

API = os.environ.get("AXONARIUM_API", "https://axonarium.com/api/v1")
VERSION = "0.1.0"
INSTRUCTIONS = """\
Axonarium is an open, cited knowledge base of neural connectivity; today it holds the mouse amygdala's
region-level inputs and outputs from the Allen Mouse Brain Connectivity Atlas. Find region IDs with
search_regions, list a region's strongest outputs or inputs with region_connections, and read the evidence
behind a connection with connection_evidence. When you state a connection, cite its claims: the source (DOI
link) and locator (the experiment), the projection density, and whether the claim is accepted or proposed
(proposed means most of the injected tracer missed the named region). Each claim's `terms` say how it may be
reused; Allen-derived claims are for non-commercial use with attribution. Densities pool both hemispheres and
count every labelled axon, including fibres of passage."""

READ_ONLY = ToolAnnotations(read_only_hint=True, idempotent_hint=True, open_world_hint=True)


def _segment(value: str) -> str:
    return quote(value, safe="")


def _claim(claim: dict[str, Any]) -> dict[str, Any]:
    """A claim as an answer needs it: what was found, how strongly, and how to cite and reuse it."""
    cited = claim["citation"]
    url = (f"https://doi.org/{cited['doi']}" if cited.get("doi")
           else f"https://pubmed.ncbi.nlm.nih.gov/{cited['pmid']}/" if cited.get("pmid") else None)
    density = next((m["value"] for m in claim.get("measurements") or [] if m["quantity"] == "projection_density"), None)
    terms = claim["terms"]
    return {
        "id": claim["id"],
        "finding": claim["paraphrase"],
        "result": claim["result"],
        "evidence_class": claim["evidence_class"],
        "projection_density": density,
        "status": claim["status"],
        "citation": {"source": cited["source"], "url": url, "locator": cited["locator"]},
        "terms": f"{terms['name']}: {terms['note']}" if terms.get("note") else terms["name"],
        "page": f"https://axonarium.com/claims/{_segment(claim['id'])}",
    }


def create(http: httpx.Client | None = None) -> MCPServer:
    """The server, reading the API through this client (tests pass one with a mocked transport)."""
    http = http or httpx.Client(base_url=API, timeout=30, headers={"User-Agent": f"axonarium-mcp/{VERSION}"})
    server = MCPServer("axonarium", instructions=INSTRUCTIONS, website_url="https://axonarium.com", version=VERSION)

    def get(path: str, **params: Any) -> Any:
        response = http.get(path.lstrip("/"), params={k: v for k, v in params.items() if v is not None})
        if response.status_code in (400, 404):
            raise ToolError(response.json().get("error", f"HTTP {response.status_code}"))  # shown to the agent
        response.raise_for_status()
        return response.json()

    @server.tool(annotations=READ_ONLY)
    def search_regions(query: str, atlas: str | None = None, limit: int = 10) -> dict[str, Any]:
        """Find brain regions by part of a name or acronym, such as "basolateral", "BLA" or "thalamus". Returns
        region IDs (such as MBA:295) for the other tools, and whether each region is in the amygdala."""
        found = get("/regions", q=query, atlas=atlas, limit=limit)
        return {"regions": found["items"], "total": found["total"]}

    @server.tool(annotations=READ_ONLY)
    def region_connections(region_id: str, direction: Literal["outputs", "inputs"] = "outputs", min_density: float = 0.0,
                           limit: int = 20) -> dict[str, Any]:
        """A region's connections, strongest projection density first: its outputs (regions it projects to) or
        inputs (regions that project to it), with claim counts and the connection IDs that connection_evidence
        takes."""
        found = get(f"/regions/{_segment(region_id)}")
        links = [link for link in found[direction] if (link["density"] or 0) >= min_density]
        return {"region": found["region"], "direction": direction, "connections": links[:limit], "total": len(found[direction])}

    @server.tool(annotations=READ_ONLY)
    def find_connections(subject: str | None = None, object: str | None = None, min_density: float | None = None,
                         limit: int = 20) -> dict[str, Any]:
        """Connections between regions, strongest projection density first. Filter by the projecting region
        (subject) and the receiving region (object), each a region ID."""
        found = get("/connections", subject=subject, object=object, min_density=min_density, limit=limit)
        return {"connections": found["items"], "total": found["total"]}

    @server.tool(annotations=READ_ONLY)
    def connection_evidence(connection_id: str) -> dict[str, Any]:
        """The claims behind one connection: what each experiment or paper found, how strongly, its citation
        (source URL and locator), whether it is accepted or proposed, and the terms it may be reused under. Cite
        these claims when you answer."""
        found = get(f"/connections/{_segment(connection_id)}")
        claims = found.pop("claims_detail")
        return {**found, "page": f"https://axonarium.com/edges/{_segment(connection_id)}", "claims": [_claim(c) for c in claims]}

    return server


def main() -> None:
    logging.getLogger("httpx").setLevel(logging.WARNING)  # one line per API request is noise in a client's log
    create().run()  # stdio, for MCP clients such as Claude Code and Claude Desktop
