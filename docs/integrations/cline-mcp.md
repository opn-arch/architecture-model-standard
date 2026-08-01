# Architecture Model MCP Server — Cline Setup

## Prerequisites

```bash
pip install opencode-arch
```

## Configuration

Add to Cline's MCP settings (VS Code settings or `cline_mcp_settings.json`):

```json
{
  "mcpServers": {
    "arch-model": {
      "command": "python",
      "args": ["-m", "opencode_arch.mcp.server"],
      "disabled": false
    }
  }
}
```

Or via Cline's UI: Settings > MCP Servers > Add Server > Enter:
- Name: `arch-model`
- Command: `python -m opencode_arch.mcp.server`

## Usage with Cline

Cline will automatically discover the MCP tools. You can prompt it:

> "Use architect_scan to understand this project's structure, then architect_slice to get compressed context"

> "Validate my architecture model using architect_validate"

## Recommended Workflow

Add to your Cline custom instructions:

```
Before making architectural changes, always:
1. Call architect_slice to understand current architecture
2. After changes, call architect_check to verify model is still representative
```
