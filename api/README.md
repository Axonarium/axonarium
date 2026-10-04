# API

Axonarium's read API is served by the site at **https://axonarium.com/api/v1** ([ADR 0013](../docs/decisions/0013-read-api.md)). Its OpenAPI 3.1 contract is at [/api/v1/openapi.json](https://axonarium.com/api/v1/openapi.json); the source is [site/lib/openapi.ts](../site/lib/openapi.ts).

| Endpoint | Returns |
| --- | --- |
| `GET /regions?q=&atlas=&amygdala=&limit=&offset=` | Atlas regions, by ID; `q` matches part of a name or acronym |
| `GET /regions/{id}` | A region (such as `MBA:295`) with its subregions, outputs and inputs |
| `GET /connections?subject=&object=&species=&predicate=&min_density=&limit=&offset=` | Connections, strongest projection density first |
| `GET /connections/{id}` | A connection (`subject\|predicate\|object\|species`, URL-encoded) with every claim behind it |
| `GET /claims/{id}` | One claim, with its citation |
| `GET /sources/{id}` | A cited source, such as `doi:10.1038/nature13186` |

Pages hold up to 200 items (`limit`, default 50). Responses are cached for five minutes. Errors come as `{"error": "…"}` with status 400, 404 or 503.

```bash
curl 'https://axonarium.com/api/v1/connections?subject=MBA:295&min_density=0.2'
curl 'https://axonarium.com/api/v1/regions/MBA%3A131'
```

## Reuse terms

Every claim carries `terms`. Claims in this repository are **CC BY 4.0**. Claims made from the Allen Mouse Brain Connectivity Atlas carry the **Allen Institute's terms of use**: non-commercial use, citing Oh et al. 2014 (doi:10.1038/nature13186) and the atlas; they are not part of the downloadable dumps. Each connection lists the terms of its claims.

## MCP server

[api/mcp](mcp/) is an MCP server over this API, so AI agents can answer pathway questions with citations.
