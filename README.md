# soif-mcp 💧🔌

**MCP server for [soif](https://github.com/Unchained-Labs/soif)** — lets any MCP client
(Claude Code, Claude Desktop, Cursor, agent frameworks) estimate the **water footprint of
LLM usage** and route models by water cost.

All figures are millilitres of freshwater consumed, returned as `{low, mid, high}`
scenario ranges with explicit assumptions — see the
[methodology](https://unchained-labs.github.io/soif/methodology/).

## Tools

| Tool | What it does |
|---|---|
| `estimate_water` | Water for one call from model + tokens (or prompt text), incl. reasoning effort, provider/region overrides |
| `estimate_from_usage` | The accurate path: feed a real OpenAI/Anthropic `usage` object |
| `compare_models` | Rank candidate models least- to most-thirsty for a workload |
| `pick_low_water_model` | Route a step: least-thirsty model above a capability floor (`min_tier`) |
| `list_known_models` | Registry of recognised models with tier/provider defaults |

Plus a `soif://methodology` resource summarising how estimates are computed.

## Install & connect

Requires Python ≥ 3.10. Once released to PyPI, `uvx soif-mcp` just works; from git today:

```bash
uv tool install "soif-mcp @ git+https://github.com/Unchained-Labs/soif-mcp.git"
# or: pipx install "soif-mcp @ git+https://github.com/Unchained-Labs/soif-mcp.git"
```

**Claude Code**

```bash
claude mcp add soif -- soif-mcp
# or without installing first:
claude mcp add soif -- uvx --from "git+https://github.com/Unchained-Labs/soif-mcp.git" soif-mcp
```

**Claude Desktop / any JSON-config client** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "soif": { "command": "soif-mcp" }
  }
}
```

**Cursor** (`.cursor/mcp.json`): same shape as above.

The server speaks stdio (the standard transport for local servers); no network access,
no credentials, no state.

## Example prompts once connected

- *"How much water did that last answer cost? Here's the usage object: …"*
- *"Compare gpt-4o, gpt-4o-mini and gemini-2.5-flash on water for a 2k-in/500-out workload."*
- *"Pick the least-thirsty model of these that's at least medium tier."*

## Publishing / marketplaces

Registries worth listing this server in (in rough order of impact):

1. **[Official MCP Registry](https://registry.modelcontextprotocol.io)** — the canonical
   registry (publish via `mcp-publisher` CLI with a `server.json`); most clients and
   sub-registries sync from it.
2. **[GitHub MCP Registry](https://github.com/mcp)** — surfaced directly in GitHub and
   VS Code/Copilot.
3. **[Smithery](https://smithery.ai)** — largest community registry; hosted install
   pages and one-line client setup.
4. **[PulseMCP](https://www.pulsemcp.com)** and **[Glama](https://glama.ai/mcp/servers)**
   — widely-browsed directories, auto-index from the official registry/GitHub.
5. **[mcp.so](https://mcp.so)** — community directory, simple PR/submit flow.
6. **[Docker MCP Catalog](https://hub.docker.com/mcp)** — if a container image is
   published; used by Docker Desktop's MCP Toolkit.
7. **Cline MCP Marketplace** — in-editor marketplace for the Cline agent (submit via
   their GitHub repo).
8. **PyPI itself** — `uvx soif-mcp` is the install path most registries point at, so the
   PyPI release (see `release.yml`) underpins all of the above.

## Development

```bash
pip install "soif-llm @ git+https://github.com/Unchained-Labs/soif.git"
pip install -e ".[dev]"
pytest && ruff check .
```

## License

MIT
