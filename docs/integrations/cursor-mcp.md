# Architecture Model MCP Server — Cursor Setup

## Prerequisites

```bash
pip install opencode-arch
```

## Configuration

Add to your Cursor MCP settings (`.cursor/mcp.json` in project root or global settings):

```json
{
  "mcpServers": {
    "arch-model": {
      "command": "python",
      "args": ["-m", "opencode_arch.mcp.server"],
      "env": {}
    }
  }
}
```

## Available Tools

Once configured, Cursor's agent can use these tools:

| Tool | Purpose |
|------|---------|
| `architect_scan` | Scan repo structure (AST analysis) |
| `architect_slice` | Get compressed context (token arbitrage) |
| `architect_validate` | Validate architecture model |
| `architect_extract` | Store architecture extraction |
| `architect_group` | Group modules into components |
| `architect_check` | Verify model representativeness |

## Workflow

1. **First time:** Agent calls `architect_scan` then `architect_group` then produces model then `architect_validate` then `architect_extract`
2. **Ongoing:** Agent calls `architect_slice` to get compressed context before reasoning about changes

## Token Savings

The `architect_slice` tool compresses your entire codebase into ~4000 tokens of dense context. For a 50K-line project, this represents ~50x compression while preserving architectural understanding.
