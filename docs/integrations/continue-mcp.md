# Architecture Model MCP Server — Continue Setup

## Prerequisites

```bash
pip install opencode-arch
```

## Configuration

Add to your Continue config (`~/.continue/config.json` or `.continue/config.json`):

```json
{
  "experimental": {
    "modelContextProtocolServers": [
      {
        "transport": {
          "type": "stdio",
          "command": "python",
          "args": ["-m", "opencode_arch.mcp.server"]
        }
      }
    ]
  }
}
```

## Usage

Continue will expose the architecture tools as context providers. Use them via:

- `@arch-model` context provider — automatically slices relevant architecture context
- Direct tool calls in chat — ask Continue to call `architect_scan`, `architect_slice`, etc.

## Context Provider Setup

For automatic architecture context in every conversation, add to config:

```json
{
  "contextProviders": [
    {
      "name": "architecture",
      "params": {
        "command": "python",
        "args": ["-m", "opencode_arch.mcp.server", "--slice", "--budget", "2000"]
      }
    }
  ]
}
```

This injects compressed architecture context into every prompt automatically.
