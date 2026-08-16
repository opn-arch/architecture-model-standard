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
            snap = ModelSnapshot(
                **{k: v for k, v in data.items() if k in ModelSnapshot.__dataclass_fields__}
            )
            # Try to load cached model YAML
            model_cache = cache_dir / f"{sha}.model.yaml"
            if model_cache.exists():
                try:
                    from architecture_model.core.parser import load_model

                    snap.model = load_model(str(model_cache))
                    # Restore file maps if available
                    maps_file = cache_dir / f"{sha}.maps.json"
                    if maps_file.exists():
                        maps = json.loads(maps_file.read_text())
                        snap.model._file_component_map = maps.get("file_component_map", {})
                        snap.model._file_system_map = maps.get("file_system_map", {})
                        snap._file_map = maps.get("file_component_map", {})
                        snap._file_system_map = maps.get("file_system_map", {})
                    # Restore sub-model data for Phase 2 context
                    sub_file = cache_dir / f"{sha}.sub_models.json"
                    if sub_file.exists():
                        snap.model._sub_models_data = json.loads(sub_file.read_text())
                    # Restore import graph if available
                    graph_file = cache_dir / f"{sha}.import_graph.json"
                    if graph_file.exists():
                        graph_data = json.loads(graph_file.read_text())
                        snap.model._import_graph = {
                            k: set(v) for k, v in graph_data.get("forward", {}).items()
                        }
                        snap.model._reverse_import_graph = {
                            k: set(v) for k, v in graph_data.get("reverse", {}).items()
                        }
                except Exception:
                    pass
            return snap

    t0 = time.monotonic()
    snapshot = ModelSnapshot(sha=sha, date="")

    try:
        # Run pipeline
        from architecture_model.pipeline.coordinator import PipelineCoordinator
        from architecture_model.pipeline.observe import ObserveStage
        from architecture_model.pipeline.infer import InferStage
        from architecture_model.pipeline.allocate import AllocateStage
        from architecture_model.pipeline.relate import RelateStage
        from architecture_model.pipeline.specify import SpecifyStage
        from architecture_model.pipeline.contract import ContractStage
        from architecture_model.pipeline.validate import ValidateStage
        from architecture_model.pipeline.decompose import DecomposeStage
        from architecture_model.pipeline.synthesize import SynthesizeStage
        from architecture_model.pipeline.emit import EmitStage
        from architecture_model.pipeline.protocol import PipelineContext
        from architecture_model.core.validator import validate_model

        stages = {
            "observe": ObserveStage(),
            "infer": InferStage(),
            "allocate": AllocateStage(),
            "relate": RelateStage(),
            "specify": SpecifyStage(),
            "contract": ContractStage(),
            "validate": ValidateStage(),
            "decompose": DecomposeStage(),
            "synthesize": SynthesizeStage(),
            "emit": EmitStage(),
        }
        coordinator = PipelineCoordinator(stages)
        ctx = PipelineContext(repo_path=repo_dir, output_dir=repo_dir / ".architecture")
        ctx.config["coordinator"] = coordinator  # Enable recursive sub-pipeline in synthesize
        results = coordinator.run_all(ctx)

        # Extract import graph from observe stage for slice expansion
        observe_result = results.get("observe")
        import_graph: dict[str, set[str]] = {}  # file → set of files it imports
        reverse_graph: dict[str, set[str]] = {}  # file → set of files that import it
        if observe_result and hasattr(observe_result, "output") and observe_result.output:
            for edge in observe_result.output.edges:
                src = str(edge.source)
                tgt = str(edge.target)
                import_graph.setdefault(src, set()).add(tgt)
                reverse_graph.setdefault(tgt, set()).add(src)

        # Extract file→component mapping from allocate stage (top-level = systems)
        alloc_result = results.get("allocate")
        file_component_map: dict[str, str] = {}
        file_system_map: dict[str, str] = {}
        if alloc_result and hasattr(alloc_result, "output") and alloc_result.output:
            for comp in alloc_result.output.components:
                for f in comp.files:
                    file_system_map[str(f)] = comp.id  # Top-level = system-level

        # Also gather file maps from sub-pipeline allocate results (synthesize stage)
        # and collect realizes relationships from sub-pipeline relate stages
        realizes_pairs: list[tuple[str, str]] = []  # (component_id, capability_id)
        synth_result = results.get("synthesize")
        if synth_result and hasattr(synth_result, "output") and synth_result.output:
            for sm in getattr(synth_result.output, "system_models", []):
                sub_results = getattr(sm, "stage_results", {})
                sub_alloc = sub_results.get("allocate")
                if sub_alloc and hasattr(sub_alloc, "output") and sub_alloc.output:
                    for comp in sub_alloc.output.components:
                        for f in comp.files:
                            file_component_map[str(f)] = comp.id
                # Collect realizes from sub-pipeline relate
                sub_relate = sub_results.get("relate")
                if sub_relate and hasattr(sub_relate, "output") and sub_relate.output:
                    for rel in sub_relate.output.relationships:
                        if rel.rel_type == "realizes":
                            realizes_pairs.append((rel.from_id, rel.to_id))

        # If no sub-pipeline results, fall back to top-level
        if not file_component_map:
            file_component_map = dict(file_system_map)

        # Store on snapshot for evaluators
        snapshot._file_map = file_component_map
        snapshot._file_system_map = file_system_map
        snapshot._alloc_components = (
            alloc_result.output.components if alloc_result and alloc_result.output else []
        )

        # Get model from emit output (emit writes to .architecture/.architecture-models/)
        model_path = (
            repo_dir / ".architecture" / ".architecture-models" / ".architecture-model.yaml"
        )
        if not model_path.exists():
            model_path = repo_dir / ".architecture-model.yaml"
        if model_path.exists():
            from architecture_model.core.parser import load_model

            model = load_model(str(model_path))
            # Inject file→component map from allocate stage onto model for evaluators
            model._file_component_map = file_component_map
            model._file_system_map = file_system_map
            model._import_graph = import_graph
            model._reverse_import_graph = reverse_graph
            # Inject sub-model realizes relationships for regen scoring
            model._sub_realizes = realizes_pairs
            snapshot.model = model

            # Validation
            val_result = validate_model(model)
            snapshot.validation_score = val_result.score

            # Counts — use components if available, else systems; include sub-model components
            comps = model.entities.components or []
            systems = model.entities.systems or []
            # Count components from sub-models via file_component_map (unique comp IDs)
            unique_comp_ids = set(file_component_map.values())
            snapshot.component_count = (
                len(unique_comp_ids) if unique_comp_ids else (len(comps) if comps else len(systems))
            )
            snapshot.capability_count = (
                len(model.entities.capabilities) if model.entities.capabilities else 0
            )
            snapshot.behavior_count = (
                len(model.entities.behaviors) if model.entities.behaviors else 0
            )
            snapshot.relationship_count = len(model.relationships) if model.relationships else 0

            # File coverage — gather from components and systems
            model_files = set()
            for entity in list(comps) + list(systems):
                if hasattr(entity, "files"):
                    model_files.update(entity.files or [])

            # Count Python files in src/ (fallback to repo root)
            src_dir = repo_dir / "src"
            if not src_dir.exists():
                src_dir = repo_dir
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
        # Cache model YAML for Phase 2
        if snapshot.model:
            model_path_out = cache_dir / f"{sha}.model.yaml"
            # Find the model YAML that was written during extraction
            for mp in [
                repo_dir / ".architecture" / ".architecture-models" / ".architecture-model.yaml",
                repo_dir / ".architecture-model.yaml",
            ]:
                if mp.exists():
                    model_path_out.write_text(mp.read_text())
                    break
            # Cache file maps
            maps_file = cache_dir / f"{sha}.maps.json"
            maps_file.write_text(
                json.dumps(
                    {
                        "file_component_map": file_component_map,
                        "file_system_map": file_system_map,
                    }
                )
            )
            # Cache import graph for Phase 2 impact analysis
            if import_graph or reverse_graph:
                graph_file = cache_dir / f"{sha}.import_graph.json"
                graph_file.write_text(
                    json.dumps(
                        {
                            "forward": {k: list(v) for k, v in import_graph.items()},
                            "reverse": {k: list(v) for k, v in reverse_graph.items()},
                        }
                    )
                )
            # Cache sub-model data for rich Phase 2 context
            sub_models_dir = repo_dir / ".architecture" / ".architecture-models"
            if sub_models_dir.exists():
                from architecture_model.core.parser import load_model as _load_sub

                sub_data = {}
                for subdir in sub_models_dir.iterdir():
                    if not subdir.is_dir():
                        continue
                    sub_model_file = subdir / ".architecture-model.yaml"
                    if not sub_model_file.exists():
                        continue
                    try:
                        sm = _load_sub(str(sub_model_file))
                        sub_data[subdir.name] = {
                            "components": [
                                {
                                    "id": c.id,
                                    "name": c.name,
                                    "description": getattr(c, "description", "") or "",
                                    "files": list(c.files or []),
                                }
                                for c in (sm.entities.components or [])
                            ],
                            "relationships": [
                                {
                                    "from": r.from_id,
                                    "to": r.to_id,
                                    "type": r.type.value
                                    if hasattr(r.type, "value")
                                    else str(r.type),
                                }
                                for r in (sm.relationships or [])
                            ],
                        }
                    except Exception:
                        pass
                if sub_data:
                    sub_file = cache_dir / f"{sha}.sub_models.json"
                    sub_file.write_text(json.dumps(sub_data))

    return snapshot
