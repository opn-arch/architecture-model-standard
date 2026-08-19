---
document: Deployment Guide
system: architecture-model-standard
system_id: SYS-unknown
generated_at: 2026-08-19T16:59:54Z
generator_version: 0.3.0
model_hash: 435262313fec
edition: 1
---

# Deployment Guide: architecture-model-standard

## Technology Constraints

- **Python >=3.11** (technology): —
- **CI/CD: GitHub Actions** (technology): —

## Component Deployment

| Component | Kind | Layer |
|-----------|------|-------|
| Core | library | foundation |
| Type System | library | foundation |
| Validation | library | foundation |
| Parser & Persistence | library | foundation |
| Model Operations | library | foundation |
| Quality Metrics | library | foundation |
| Pipeline | service | domain |
| Pipeline Coordination | service | domain |
| Observation Stages | service | domain |
| Allocation & Relation Stages | service | domain |
| Specification & Contract Stages | service | domain |
| Synthesis & Emit Stages | service | domain |
| Manifest | library | domain |
| Scanners | library | domain |
| Graph & Analysis | library | domain |
| Grouping & Generation | library | domain |
| Documentation | library | application |
| Core Doc Generators | library | application |
| SE Document Suite | library | application |
| Orchestration | service | application |
| Enrichment | service | application |
| Decomposition | service | application |
| Extract | library | domain |
| Authoring | library | application |
| CLI | service | interface |
| Configuration | library | infrastructure |
| Export | library | application |
| Pipeline Learning | library | domain |
| Utilities | library | infrastructure |
