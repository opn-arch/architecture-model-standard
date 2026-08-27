---
document: Logical Architecture
system: architecture-model-standard/Cli
system_id: SYS-unknown
generated_at: 2026-08-27T14:23:22Z
generator_version: 0.3.0
model_hash: fae5761683d2
edition: 1
---

# Logical Architecture: architecture-model-standard/Cli

## Layer Structure

*No layers defined.*

## Component Allocation

### LYR-CLI

| Component | Kind | Files | Responsibilities |
|-----------|------|-------|------------------|
| CLI (COMP-CLI) | application | 3 files | — |

*Intent:* Wire argparse subcommands to core library functions (parser, validator, slicer, differ, pipeline coordinator) and format their output for terminal consumption

*Trade-offs:*
- Uses stdlib argparse rather than click/typer, keeping zero external CLI dependencies but sacrificing richer UX features (auto-completion, colored help)
- Monolithic main.py (~900 lines) trades modularity for single-file simplicity and easy grep-ability


## Inter-Component Interfaces

| Interface | Type | Protocol | Provider | Consumer |
|-----------|------|----------|----------|----------|
| CLI Interface | cli | — | — | — |

## Dependency Graph

```mermaid
graph TD
```
