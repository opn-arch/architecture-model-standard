# Deployment Guide — Architecture Model

## 1. Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.10+ |
| pip / pipx | latest |
| Git | 2.x+ |

No external services required — this is a CLI/library tool, not a hosted service.

## 2. Build Process

```bash
# Clone and install
git clone <repo-url> && cd architecture-model

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install with dependencies
pip install -e .

# Run tests
python -m pytest
```

## 3. Deployment Steps

This project deploys as a **Python package** (not a service). Deployment means publishing or installing.

### Local Install

```bash
pip install -e .
```

### Package Publishing

```bash
pip install build twine

python -m build
twine upload dist/*
```

### CI/CD (typical pattern)

```yaml
# .github/workflows/release.yml
name: Release
on:
  push:
    tags: ['v*']
jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      - run: pip install build twine
      - run: python -m build
      - run: twine upload dist/*
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}
```

## 4. Environment Configuration

| Variable | Purpose | Default |
|----------|---------|---------|
| `ARCH_MODEL_CONFIG` | Path to config YAML | `./architecture.yaml` |
| `ARCH_MODEL_PROFILE` | Domain profile to load | `default` |
| `ARCH_MODEL_CACHE_DIR` | Pipeline cache directory | `./.arch_cache` |

Configuration is loaded via `src/architecture_model/config/loader.py` and supports YAML files with schema validation (`config/schema.py`).

## 5. Verification

```bash
# Verify installation
python -m architecture_model --help

# Run validation on a model
python -m architecture_model validate ./model.yaml

# Run test suite
python -m pytest --tb=short

# Smoke test pipeline
python -m architecture_model manifest --path ./src
```

## 6. Rollback

### Package rollback

```bash
# Pin to previous version
pip install architecture-model==<previous-version>
```

### Git-based rollback

```bash
git revert <bad-commit>
# or
git checkout tags/v<previous> -b hotfix
pip install -e .
```

Since this is a stateless CLI tool with no database or persistent service, rollback is simply reverting to a prior package version.