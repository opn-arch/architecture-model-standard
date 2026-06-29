# Project Descriptor Reference

## 1. Overview

The `.architecture-model.yaml` file is the project descriptor that tells the Architecture Model Standard package how your project is structured. It lives in your project root directory.

**Without this file**: The package uses auto-discovery heuristics (works for simple projects).
**With this file**: Full control over functional decomposition, layer mapping, and metrics.

---

## 2. File Location

```
my-project/
  .architecture-model.yaml    <-- Here
  src/
  tests/
  ...
```

The package searches for this file in the project root passed to any API function.

---

## 3. Full Schema

```yaml
# .architecture-model.yaml — Architecture Model Project Descriptor

project:
  name: string          # Project identifier (used in output paths)
  system: string        # Human-readable system name

output:
  model: string         # Path template for model YAML (supports {project})
  manifest: string      # Path template for reality manifest
  artifacts: string     # Path template for generated artifacts directory

layers:
  <layer-id>:           # Unique layer identifier (e.g., "web-layer")
    dirs: [string]      # Source directories belonging to this layer
    description: string # Optional description

functional_blocks:
  <block-id>:           # Unique block ID (e.g., "F1")
    name: string        # Human-readable block name
    dirs: [string]      # Directories to scan for this block
    files: [string]     # Explicit files belonging to this block
    description_source: string  # Optional provenance tag

metrics:
  - label: string       # Metric name (becomes {label}_count in manifest)
    path: string        # Directory to count files in
    pattern: string     # Glob pattern (default: "*.py")
    exclude: [string]   # Filenames to exclude
    recursive: boolean  # Use rglob instead of glob (default: false)
```

---

## 4. Section Reference

### 4.1 `project`

Identifies the project. The `name` field is used in path templates.

```yaml
project:
  name: logs-db
  system: Knowledge OS
```

### 4.2 `output`

Path templates for generated artifacts. Use `{project}` as a placeholder that gets replaced with `project.name`.

```yaml
output:
  model: "output/{project}/architecture-model.yaml"
  manifest: "output/{project}/reality-manifest.json"
  artifacts: "output/{project}/artifacts/stage2"
```

**Default values** (used if section is omitted):
- model: `output/{project}/architecture-model.yaml`
- manifest: `output/{project}/reality-manifest.json`
- artifacts: `output/{project}/artifacts/stage2`

### 4.3 `layers`

Defines the logical architecture layers. Each layer maps to one or more source directories. The layer ID is used as a relationship target in the model.

```yaml
layers:
  web-layer:
    dirs: [app/routers, app/schemas, app/templates]
  services-layer:
    dirs: [app/services]
  pipeline-layer:
    dirs: [scripts]
  data-layer:
    dirs: [app/models, alembic]
```

**Used by**:
- Manifest generator: determines which directories to scan
- Merger: maps new components to layers
- Slicers: groups modules by layer for LLM context

### 4.4 `functional_blocks`

The core architectural decomposition. Each block represents a top-level capability of the system. Files and directories listed here are scanned to build the reality manifest.

```yaml
functional_blocks:
  F1:
    name: "Ingest Source Data"
    dirs: [scripts/ingestion]
    files:
      - scripts/_pipeline_ingest.py
      - scripts/_pipeline_folder_intel.py
    description_source: "process:ingest"
```

**Conventions**:
- Block IDs are typically `F1`, `F2`, ... `FN`
- `dirs`: All `.py` files in these directories belong to this block
- `files`: Explicit files that don't fall under any directory
- A file can only belong to ONE block (first match wins)
- `description_source`: Optional tag for linking to process documentation

**Used by**:
- Manifest generator: scans blocks to build sub-function inventory
- Merger: assigns f_block to auto-discovered components
- Model extractor: creates Capability entities from blocks

### 4.5 `metrics`

Defines countable project metrics. Each metric produces a `{label}_count` entry in the reality manifest.

```yaml
metrics:
  - label: router
    path: app/routers
    pattern: "*.py"
    exclude: [__init__.py]
  - label: template
    path: app/templates
    pattern: "**/*.html"
    recursive: true
```

**Fields**:
- `label`: Becomes the metric key (`{label}_count`)
- `path`: Directory to count files in (relative to project root)
- `pattern`: Glob pattern for matching files (default: `"*.py"`)
- `exclude`: Filenames to skip (e.g., `__init__.py`)
- `recursive`: If true, uses `rglob` to search subdirectories

**Note**: `total_python_files` is always computed automatically (not configurable).

---

## 5. Auto-Discovery

If no `.architecture-model.yaml` exists, the package auto-discovers:

### Layer Discovery

Checks for common directory patterns:
- `app/routers`, `app/views`, `app/api` → web-layer
- `app/services`, `src/services` → services-layer
- `app/models`, `src/models`, `alembic` → data-layer
- `scripts`, `pipeline` → pipeline-layer
- `app/tasks`, `tasks/` → scheduling-layer

### Metric Discovery

Checks for common countable directories:
- `app/routers` → router_count
- `app/models` → model_count
- `alembic/versions` → migration_count
- `app/templates` → template_count

### Functional Blocks

**Not auto-discovered.** Functional decomposition requires human architectural judgment. Without config, the manifest generator scans all Python files without block assignment.

---

## 6. Minimal Config

The smallest useful config just needs project name and functional blocks:

```yaml
project:
  name: my-app

functional_blocks:
  F1:
    name: "Core Logic"
    dirs: [src/core]
  F2:
    name: "API Layer"
    dirs: [src/api]
  F3:
    name: "Data Access"
    dirs: [src/models]
```

Everything else (layers, metrics, output paths) will use auto-discovery or defaults.

---

## 7. Examples

### FastAPI Project

```yaml
project:
  name: my-fastapi-app
  system: Order Management System

layers:
  api-layer:
    dirs: [app/api, app/schemas]
  domain-layer:
    dirs: [app/domain, app/services]
  infra-layer:
    dirs: [app/db, app/external]

functional_blocks:
  F1:
    name: "Order Processing"
    dirs: [app/domain/orders]
    files: [app/api/orders.py]
  F2:
    name: "Inventory Management"
    dirs: [app/domain/inventory]
    files: [app/api/inventory.py]
  F3:
    name: "User Management"
    dirs: [app/domain/users]
    files: [app/api/auth.py, app/api/users.py]

metrics:
  - label: endpoint
    path: app/api
    pattern: "*.py"
    exclude: [__init__.py]
  - label: model
    path: app/db/models
    pattern: "*.py"
    exclude: [__init__.py, base.py]
```

### Django Project

```yaml
project:
  name: my-django-app
  system: CMS Platform

layers:
  views-layer:
    dirs: [apps/*/views]
  models-layer:
    dirs: [apps/*/models]
  templates-layer:
    dirs: [templates]

functional_blocks:
  F1:
    name: "Content Management"
    dirs: [apps/content]
  F2:
    name: "User Accounts"
    dirs: [apps/accounts]
  F3:
    name: "Media Processing"
    dirs: [apps/media]

metrics:
  - label: migration
    path: apps
    pattern: "**/migrations/*.py"
    recursive: true
    exclude: [__init__.py]
```

### Monorepo (Multiple Services)

```yaml
project:
  name: platform
  system: E-Commerce Platform

layers:
  gateway-layer:
    dirs: [services/gateway/src]
  orders-layer:
    dirs: [services/orders/src]
  payments-layer:
    dirs: [services/payments/src]
  shared-layer:
    dirs: [packages/shared/src]

functional_blocks:
  F1:
    name: "API Gateway"
    dirs: [services/gateway/src]
  F2:
    name: "Order Fulfillment"
    dirs: [services/orders/src]
  F3:
    name: "Payment Processing"
    dirs: [services/payments/src]
```
