# Operations Manual — Architecture Model System

## 1. Deployment

### Prerequisites

- Python ≥ 3.11
- GitHub Actions for CI/CD

### Installation

```bash
# Clone and install
git clone <repo-url>
cd architecture-model
pip install -e .
```

### Running

```bash
# Via module entry point
python -m architecture_model

# Or via CLI
architecture-model --help
```

### CI/CD (GitHub Actions)

Deployments are automated via GitHub Actions (CON-2). Typical workflow:

```yaml
# .github/workflows/deploy.yml
name: Deploy
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -e .
      - run: python -m pytest
```

## 2. Configuration

### Config Files

| File | Purpose |
|------|---------|
| `src/architecture_model/config/loader.py` | Config loading logic |
| `src/architecture_model/config/schema.py` | Config schema definitions |
| `src/architecture_model/profiles/builtins/__init__.py` | Built-in domain profiles |

### Configuration Loading

```python
# Inferred pattern from config/loader.py
from architecture_model.config.loader import load_config

config = load_config("path/to/config.yaml")
```

### Domain Profiles

Profiles customize behavior per domain. Located in `src/architecture_model/profiles/builtins/`.

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `ARCH_MODEL_CONFIG` | Path to config file (inferred) |
| `ARCH_MODEL_CACHE_DIR` | Pipeline cache directory |
| `ARCH_MODEL_LOG_LEVEL` | Logging verbosity |

## 3. Monitoring & Health

### Health Checks

```bash
# Health report generation
python -m architecture_model docs health
```

Key files:
- `src/architecture_model/monitoring.py` — Runtime monitoring
- `src/architecture_model/monitoring_checks.py` — Health check definitions
- `src/architecture_model/docs/health.py` — Health report generation

### Observability

- **Drift detection**: `src/architecture_model/docs/drift.py`
- **Confidence scoring**: `src/architecture_model/core/confidence.py`
- **Regen readiness**: `src/architecture_model/core/regen_readiness.py`

### Logging

```python
import logging
logging.getLogger("architecture_model").setLevel("DEBUG")
```

## 4. Common Operations

### Generate Architecture Model

```bash
python -m architecture_model pipeline run --source ./my-project
```

### Generate Documentation

```bash
python -m architecture_model docs generate --output ./docs/
python -m architecture_model docs se generate  # SE document suite
```

### Export for AI Consumption

```bash
python -m architecture_model export flatfiles --output ./export/
```

### Cache Management

Pipeline caching is handled by `src/architecture_model/pipeline/cache.py`.

```bash
# Clear cache (inferred)
python -m architecture_model cache clear
```

### Model Validation

```bash
python -m architecture_model validate model.yaml
```

## 5. Troubleshooting

| Issue | Resolution |
|-------|-----------|
| Validation failures | Check `core/validator.py` rules — JSON schema, referential integrity, cycles |
| Stale pipeline cache | Clear cache directory and re-run |
| Scanner errors (TS/Kotlin) | Ensure source files are syntactically valid; check `manifest/ts_scanner.py`, `manifest/kt_scanner.py` |
| Low confidence scores | Run enrichment: `python -m architecture_model enrich` |
| Import resolution failures | Check `manifest/call_graph.py` — ensure project dependencies are installed |
| Pipeline stage failure | Check `pipeline/report.py` output for stage-specific errors |

## 6. Dependencies

### Runtime

| Dependency | Purpose |
|------------|---------|
| Python ≥ 3.11 | Runtime (CON-1) |
| PyYAML | YAML parsing (`core/parser.py`) |
| JSON Schema lib | Model validation (`core/validator.py`) |

### External Systems

- **Filesystem access** — Source code scanning requires read access to target repos
- **GitHub Actions** — CI/CD automation (CON-2)

### Optional

- Target language toolchains (Node.js for TS scanning, Kotlin compiler) for enhanced analysis via `manifest/ts_scanner.py` and `manifest/kt_scanner.py`