---
artifact_id: component-catalog
generated_at: 2026-07-11T16:09:02.022361+00:00
---
# Component Catalog — architecture-model-standard

## Overview

This catalog documents all components in the architecture-model-standard system. All components reside in the **L-APP** (Application) layer.

---

## Components

### COMP-CORE: core

| Field | Value |
|-------|-------|
| **ID** | COMP-CORE |
| **Name** | core |
| **Kind** | service |
| **Layer** | L-APP |
| **Status** | ACTIVE |

**Realizes:** CAP-F1, CAP-F3

**Exposes:**
- IF-PARSE-API (Parser API)
- IF-VALIDATE-API (Validator API)
- IF-SLICER-API (Slicer API)

**Constrained by:** CON-SCHEMA, CON-NO-ORPHANS

**Traces to:** BEH-VALIDATE

---

### COMP-MANIFEST: manifest

| Field | Value |
|-------|-------|
| **ID** | COMP-MANIFEST |
| **Name** | manifest |
| **Kind** | service |
| **Layer** | L-APP |
| **Status** | ACTIVE |

**Realizes:** CAP-F2

**Exposes:**
- IF-MANIFEST-API (Manifest API)

**Traces to:** BEH-MANIFEST

---

### COMP-CONFIG: config

| Field | Value |
|-------|-------|
| **ID** | COMP-CONFIG |
| **Name** | config |
| **Kind** | service |
| **Layer** | L-APP |
| **Status** | ACTIVE |

**Realizes:** CAP-F5

---

### COMP-SPEC: spec

| Field | Value |
|-------|-------|
| **ID** | COMP-SPEC |
| **Name** | spec |
| **Kind** | service |
| **Layer** | L-APP |
| **Status** | ACTIVE |

**Realizes:** CAP-F5

**Constrained by:** CON-SCHEMA

---

### COMP-CLI: cli

| Field | Value |
|-------|-------|
| **ID** | COMP-CLI |
| **Name** | cli |
| **Kind** | service |
| **Layer** | L-APP |
| **Status** | ACTIVE |

**Realizes:** CAP-F4

**Exposes:**
- IF-CLI (CLI Interface)

**Traces to:** BEH-INIT

---

### COMP-EXTRACT: extract

| Field | Value |
|-------|-------|
| **ID** | COMP-EXTRACT |
| **Name** | extract |
| **Kind** | service |
| **Layer** | L-APP |
| **Status** | ACTIVE |

**Realizes:** CAP-F6

---

### COMP-PROFILES: profiles

| Field | Value |
|-------|-------|
| **ID** | COMP-PROFILES |
| **Name** | profiles |
| **Kind** | service |
| **Layer** | L-APP |
| **Status** | ACTIVE |

**Realizes:** CAP-F7

---

### COMP-UTILS: utils

| Field | Value |
|-------|-------|
| **ID** | COMP-UTILS |
| **Name** | utils |
| **Kind** | service |
| **Layer** | L-APP |
| **Status** | ACTIVE |

---

### COMP-ENRICH: enrich

| Field | Value |
|-------|-------|
| **ID** | COMP-ENRICH |
| **Name** | enrich |
| **Kind** | service |
| **Layer** | L-APP |
| **Status** | ACTIVE |

**Realizes:** CAP-F8

---

## Component Dependencies

| Source | Target | Relationship |
|--------|--------|--------------|
| COMP-CLI | COMP-CORE | depends-on |
| COMP-CLI | COMP-CONFIG | depends-on |
| COMP-CLI | COMP-MANIFEST | depends-on |
| COMP-CLI | COMP-ENRICH | depends-on |
| COMP-CORE | COMP-CONFIG | depends-on |
| COMP-CORE | COMP-SPEC | depends-on |
| COMP-MANIFEST | COMP-CONFIG | depends-on |
| COMP-EXTRACT | COMP-CORE | depends-on |
| COMP-ENRICH | COMP-CORE | depends-on |

### Dependency Summary

- **cli** depends on: core, config, manifest, enrich
- **core** depends on: config, spec
- **manifest** depends on: config
- **extract** depends on: core
- **enrich** depends on: core
- **config** depends on: (none)
- **spec** depends on: (none)
- **profiles** depends on: (none)
- **utils** depends on: (none)

---

## External Consumers

| Actor | Interface Consumed |
|-------|--------------------|
| ACT-DEV (Developer) | IF-CLI |
| ACT-LLM (LLM Agent) | IF-PARSE-API, IF-SLICER-API |
