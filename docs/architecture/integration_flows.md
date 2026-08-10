# Integration Flows: architecture-model-standard

```mermaid
flowchart TD
  COMP-CLI[CLI] -->|depends-on| COMP-CORE[Core]
  COMP-CLI[CLI] -->|depends-on| COMP-ORCHESTRATION[Orchestration]
  COMP-CLI[CLI] -->|depends-on| COMP-PIPELINE[Pipeline]
  COMP-CLI[CLI] -->|depends-on| COMP-MANIFEST[Manifest]
  COMP-CLI[CLI] -->|depends-on| COMP-CONFIG[Config]
  COMP-ORCHESTRATION[Orchestration] -->|depends-on| COMP-CORE[Core]
  COMP-ORCHESTRATION[Orchestration] -->|depends-on| COMP-MANIFEST[Manifest]
  COMP-PIPELINE[Pipeline] -->|depends-on| COMP-CORE[Core]
  COMP-PIPELINE[Pipeline] -->|depends-on| COMP-MANIFEST[Manifest]
  COMP-PIPELINE[Pipeline] -->|depends-on| COMP-CONFIG[Config]
  COMP-EXTRACT[Extract] -->|depends-on| COMP-CORE[Core]
  COMP-EXTRACT[Extract] -->|depends-on| COMP-MANIFEST[Manifest]
  COMP-EXTRACT[Extract] -->|depends-on| COMP-CONFIG[Config]
  COMP-DOCS[Docs] -->|depends-on| COMP-CORE[Core]
  COMP-DOCS[Docs] -->|depends-on| COMP-MANIFEST[Manifest]
  COMP-EXPORT[Export] -->|depends-on| COMP-CORE[Core]
  COMP-INTEGRATIONS[Integrations] -->|depends-on| COMP-CORE[Core]
  COMP-AUTHORING[Authoring] -->|depends-on| COMP-CORE[Core]
  COMP-CORE[Core] -->|depends-on| COMP-CONFIG[Config]
  COMP-MANIFEST[Manifest] -->|depends-on| COMP-CONFIG[Config]
  COMP-MANIFEST[Manifest] -->|depends-on| COMP-UTILS[Utils]
```

## CLI → Core (depends-on)
—

**Source:** COMP-CLI (CLI)
**Target:** COMP-CORE (Core)

## CLI → Orchestration (depends-on)
—

**Source:** COMP-CLI (CLI)
**Target:** COMP-ORCHESTRATION (Orchestration)

## CLI → Pipeline (depends-on)
—

**Source:** COMP-CLI (CLI)
**Target:** COMP-PIPELINE (Pipeline)

## CLI → Manifest (depends-on)
—

**Source:** COMP-CLI (CLI)
**Target:** COMP-MANIFEST (Manifest)

## CLI → Config (depends-on)
—

**Source:** COMP-CLI (CLI)
**Target:** COMP-CONFIG (Config)

## Orchestration → Core (depends-on)
—

**Source:** COMP-ORCHESTRATION (Orchestration)
**Target:** COMP-CORE (Core)

## Orchestration → Manifest (depends-on)
—

**Source:** COMP-ORCHESTRATION (Orchestration)
**Target:** COMP-MANIFEST (Manifest)

## Pipeline → Core (depends-on)
—

**Source:** COMP-PIPELINE (Pipeline)
**Target:** COMP-CORE (Core)

## Pipeline → Manifest (depends-on)
—

**Source:** COMP-PIPELINE (Pipeline)
**Target:** COMP-MANIFEST (Manifest)

## Pipeline → Config (depends-on)
—

**Source:** COMP-PIPELINE (Pipeline)
**Target:** COMP-CONFIG (Config)

## Extract → Core (depends-on)
—

**Source:** COMP-EXTRACT (Extract)
**Target:** COMP-CORE (Core)

## Extract → Manifest (depends-on)
—

**Source:** COMP-EXTRACT (Extract)
**Target:** COMP-MANIFEST (Manifest)

## Extract → Config (depends-on)
—

**Source:** COMP-EXTRACT (Extract)
**Target:** COMP-CONFIG (Config)

## Docs → Core (depends-on)
—

**Source:** COMP-DOCS (Docs)
**Target:** COMP-CORE (Core)

## Docs → Manifest (depends-on)
—

**Source:** COMP-DOCS (Docs)
**Target:** COMP-MANIFEST (Manifest)

## Export → Core (depends-on)
—

**Source:** COMP-EXPORT (Export)
**Target:** COMP-CORE (Core)

## Integrations → Core (depends-on)
—

**Source:** COMP-INTEGRATIONS (Integrations)
**Target:** COMP-CORE (Core)

## Authoring → Core (depends-on)
—

**Source:** COMP-AUTHORING (Authoring)
**Target:** COMP-CORE (Core)

## Core → Config (depends-on)
—

**Source:** COMP-CORE (Core)
**Target:** COMP-CONFIG (Config)

## Manifest → Config (depends-on)
—

**Source:** COMP-MANIFEST (Manifest)
**Target:** COMP-CONFIG (Config)

## Manifest → Utils (depends-on)
—

**Source:** COMP-MANIFEST (Manifest)
**Target:** COMP-UTILS (Utils)
