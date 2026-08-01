# AI Tool Integrations

Architecture-model-standard works with any AI coding tool that supports MCP (Model Context Protocol) or custom rules files.

## Quick Start

| Tool | Setup Time | Method |
|------|-----------|--------|
| **OpenCode** | 30s | `opencode mcp add` (built-in) |
| **Cursor** | 2 min | [MCP config](./cursor-mcp.md) + [.cursorrules](./.cursorrules) |
| **Cline** | 2 min | [MCP config](./cline-mcp.md) |
| **Continue** | 2 min | [MCP config](./continue-mcp.md) |

## What You Get

1. **Token arbitrage** — 50x compression of codebase into architectural context
2. **Structure awareness** — Agent knows component boundaries, layers, dependencies
3. **Quality gates** — Validate and check representativeness of architecture models
4. **Generated docs** — Component specs, ICDs, health reports auto-generated

## Without MCP (any tool)

Even without MCP support, you can use:
1. `.cursorrules` / custom instructions — paste architecture rules into your tool
2. Generated docs — point your tool at `.architecture-models/docs/`
3. Manual context — copy `architect_slice` output into prompts

## Installation

```bash
pip install opencode-arch  # MCP server + CLI
# OR
pip install architecture-model-standard  # Library only (for init/docs)
```
