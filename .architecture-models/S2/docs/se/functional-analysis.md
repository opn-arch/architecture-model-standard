---
document: Functional Analysis
system: architecture-model-standard/Cli
system_id: SYS-unknown
generated_at: 2026-08-27T14:23:22Z
generator_version: 0.3.0
model_hash: fae5761683d2
edition: 1
---

# Functional Analysis: architecture-model-standard/Cli

## Capability Inventory

| ID | Capability | Priority | Status | Description | Intent |
|----|-----------|----------|--------|-------------|--------|
| CAP-CLI | Command-Line Operations | medium | ACTIVE | Expose all architecture-model operations as CLI subcommands | Provide a unified argparse-based entry point so users and CI pipelines can validate, slice, diff, enrich, and run the extraction pipeline from the terminal |

## Measures of Effectiveness

| Capability | MOE |
|---|---|
| Command-Line Operations (CAP-CLI) | Every core operation (validate, slice, diff, stats, pipeline, manifest, enrich, impact) is accessible as a subcommand |
| Command-Line Operations (CAP-CLI) | Exit codes reflect success (0) or failure (non-zero) for CI integration |
| Command-Line Operations (CAP-CLI) | Help text is auto-generated and accurate for all subcommands |

## Functional Decomposition

```mermaid
graph TD
    CAP-CLI["Command-Line Operations"]
```

## Capability-Component Mapping

| Capability | Realized By | Component Kind |
|-----------|------------|----------------|
| Command-Line Operations | CLI (COMP-CLI) | application |

### Design Trade-offs

**CLI** (COMP-CLI):
- Uses stdlib argparse rather than click/typer, keeping zero external CLI dependencies but sacrificing richer UX features (auto-completion, colored help)
- Monolithic main.py (~900 lines) trades modularity for single-file simplicity and easy grep-ability

## Behavioral Coverage

Total behaviors: 1

