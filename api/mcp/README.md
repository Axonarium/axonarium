# Axonarium MCP server

An [MCP](https://modelcontextprotocol.io) server that lets AI agents answer brain-connectivity questions from [Axonarium](https://axonarium.com), citing the evidence. It reads the public [read API](../README.md) and never writes.

## Use it

Claude Code:

```bash
claude mcp add axonarium -- uvx --from "git+https://github.com/axonarium/axonarium#subdirectory=api/mcp" axonarium-mcp
```

Claude Desktop and other MCP clients (`mcpServers` in the client's config):

```json
{
  "axonarium": {
    "command": "uvx",
    "args": ["--from", "git+https://github.com/axonarium/axonarium#subdirectory=api/mcp", "axonarium-mcp"]
  }
}
```

Then ask, for example: "What does the mouse basolateral amygdala project to most strongly, and what is the evidence?"

## Tools

| Tool | Answers |
| --- | --- |
| `search_regions` | Which region IDs match a name or acronym ("basolateral", "BLA", "thalamus") |
| `region_connections` | A region's strongest outputs or inputs, with claim counts and connection IDs |
| `find_connections` | Connections filtered by projecting and receiving region |
| `connection_evidence` | The claims behind a connection: finding, projection density, accepted or proposed, citation URL and locator, reuse terms |

The server tells the agent to cite claims and to state their terms: claims made from the Allen Mouse Brain Connectivity Atlas are for non-commercial use with attribution. Set `AXONARIUM_API` to read another deployment.

## Develop

```bash
uv run --directory api/mcp pytest
```

The tests call the tools through the MCP protocol in-process, against canned API answers.
