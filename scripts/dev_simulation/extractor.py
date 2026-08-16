"""Pipeline extractor — runs architecture extraction at each checkpoint."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


@dataclass
class ModelSnapshot:
    """Complete extraction result at a checkpoint."""

    sha: str
    date: str
    validation_score: float = 0.0
    component_count: int = 0
    capability_count: int = 0
    behavior_count: int = 0
    relationship_count: int = 0
    file_coverage: float = 0.0
    regen_overall: float = 0.0
    regen_grade: str = "F"
    extraction_time_ms: int = 0
    error: str = ""
    # Not serialized — in-memory only
    model: Any = field(default=None, repr=False)
    manifest: Any = field(default=None, repr=False)

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("model", None)
        d.pop("manifest", None)
        return d


def extract_at_checkpoint(repo_dir: Path, cache_dir: Path | None = None) -> ModelSnapshot:
    """Run full pipeline extraction on repo at current checkout state."""
    import subprocess

    # Check cache
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo_dir, capture_output=True, text=True
    ).stdout.strip()

    if cache_dir:
        cache_file = cache_dir / f"{sha}.json"
        if cache_file.exists():
            data = json.loads(cache_file.read_text())
            return ModelSnapshot(
                **{k: v for k, v in data.items() if k in ModelSnapshot.__dataclass_fields__}
            )

    t0 = time.monotonic()
    snapshot = ModelSnapshot(sha=sha, date="")

    try:
        # Run pipeline
        from architecture_model.pipeline.coordinator import PipelineCoordinator
        from architecture_model.core.validator import validate_model

        coordinator = PipelineCoordinator(project_root=repo_dir)
        result = coordinator.run()

        # Get model from emit output
        model_path = repo_dir / ".architecture-model.yaml"
        if model_path.exists():
            from architecture_model.core.parser import load_model

            model = load_model(str(model_path))
            snapshot.model = model

            # Validation
            val_result = validate_model(model)
            snapshot.validation_score = val_result.score

            # Counts
            snapshot.component_count = (
                len(model.entities.components) if model.entities.components else 0
            )
            snapshot.capability_count = (
                len(model.entities.capabilities) if model.entities.capabilities else 0
            )
            snapshot.behavior_count = (
                len(model.entities.behaviors) if model.entities.behaviors else 0
            )
            snapshot.relationship_count = len(model.relationships) if model.relationships else 0

            # File coverage
            model_files = set()
            for comp in model.entities.components or []:
                model_files.update(comp.files)

            # Count Python files in src/
            src_dir = repo_dir / "src"
            if src_dir.exists():
                all_py = list(src_dir.rglob("*.py"))
                non_trivial = [f for f in all_py if f.stat().st_size > 50]
                if non_trivial:
                    rel_files = {str(f.relative_to(repo_dir)) for f in non_trivial}
                    covered = model_files & rel_files
                    snapshot.file_coverage = len(covered) / len(rel_files) * 100

            # Regen readiness
            try:
                from architecture_model.core.regen_readiness import compute_regen_readiness

                regen = compute_regen_readiness(model)
                snapshot.regen_overall = regen.overall
                snapshot.regen_grade = regen.grade
            except Exception:
                pass

    except Exception as e:
        snapshot.error = str(e)[:200]

    snapshot.extraction_time_ms = int((time.monotonic() - t0) * 1000)

    # Cache
    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / f"{sha}.json"
        cache_file.write_text(json.dumps(snapshot.to_dict(), indent=2))

    return snapshot
