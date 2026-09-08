# tiny_repo — minimal fixture for SI&L pipeline verification (DoD B / step 3)

A deliberately small three-module Python project the AMS pipeline can walk
end-to-end. Structure is intentionally simple so the reality manifest is stable
and the emitted architecture model is easy to inspect.

```
tiny_pkg/
├── __init__.py
├── api.py       — thin surface layer (depends on core)
├── core.py      — business logic (depends on storage)
└── storage.py   — data-layer stub
```

Used by:
- `tests/sil/test_tiny_repo_pipeline.py`  (DoD step 3)
- `scripts/apply_sil_decorators.py --check`  (DoD step 6, via emitted model)
