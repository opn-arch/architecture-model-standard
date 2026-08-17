"""Emit pipeline stage — writes final SoS artifact structure to disk."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

from architecture_model.pipeline.emit_types import EmitResult
from architecture_model.pipeline.protocol import (
    Diagnostic,
    PipelineContext,
    QualityMetrics,
    StageResult,
)
from architecture_model.pipeline.synthesize_types import SynthesizeResult


def _slugify(name: str) -> str:
    """Convert name to filesystem-safe slug."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _write_file(path: Path, content: str, result: EmitResult) -> None:
    """Write a file and track in result."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    result.written_paths.append(str(path))
    result.total_bytes += len(content.encode("utf-8"))


_TEST_DIR_MARKERS = frozenset({"tests", "test", "testing", "typing_tests"})


def _is_test_path(path_str: str) -> bool:
    """Check if a file path is a test file based on directory or filename."""
    parts = Path(path_str).parts
    # Directory-based: any parent is a test dir
    if _TEST_DIR_MARKERS & set(parts[:-1]):
        return True
    # Filename-based: test_*.py or *_test.py
    stem = Path(path_str).stem
    return stem.startswith("test_") or stem.endswith("_test") or stem == "conftest"


def _build_test_map(ctx: PipelineContext) -> dict[str, list[str]]:
    """Build source→test reverse mapping from observe stage import edges.

    For each test file that imports a source file, record the reverse:
    source_file → [test files that import it].
    """
    observe_result = ctx.get("observe")
    if not observe_result or not observe_result.output:
        return {}

    source_to_tests: dict[str, list[str]] = {}
    for edge in observe_result.output.edges:
        src_str = str(edge.source)  # The file doing the importing
        tgt_str = str(edge.target)  # The file being imported

        # If importer is a test file and target is NOT a test file → source←test mapping
        if _is_test_path(src_str) and not _is_test_path(tgt_str):
            source_to_tests.setdefault(tgt_str, []).append(src_str)

    return source_to_tests


def _build_component_test_map(
    test_map: dict[str, list[str]], file_component_map: dict[str, str]
) -> dict[str, list[str]]:
    """Aggregate test_map by component ID.

    Returns: comp_id → [unique test files]
    """
    comp_tests: dict[str, set[str]] = {}
    for source_file, test_files in test_map.items():
        comp_id = file_component_map.get(source_file)
        if comp_id:
            comp_tests.setdefault(comp_id, set()).update(test_files)
    return {k: sorted(v) for k, v in comp_tests.items()}


class EmitStage:
    name = "emit"
    version = "1.0"
    requires = ["synthesize"]

    def can_run(self, ctx: PipelineContext) -> bool:
        return ctx.has("synthesize")

    def output_path(self, ctx: PipelineContext) -> Path:
        return ctx.output_dir / ".architecture-models"

    def run(self, ctx: PipelineContext) -> StageResult[EmitResult]:
        t0 = time.monotonic()

        synth: SynthesizeResult = ctx.get("synthesize").output
        out_dir = self.output_path(ctx)
        result = EmitResult(output_dir=str(out_dir))
        diagnostics: list[Diagnostic] = []

        # 1. Write SoS model
        if synth.sos_model_yaml:
            _write_file(out_dir / ".architecture-model.yaml", synth.sos_model_yaml, result)

        # 2. Write top-level manifest
        if synth.top_manifest_json:
            _write_file(out_dir / "manifest.json", synth.top_manifest_json, result)

        # 3. Write top-level reports (regenerate with accumulated LLM calls from ctx)
        if ctx.llm_calls:
            from architecture_model.pipeline.report import generate_pipeline_report

            all_results = {name: ctx.cache[name] for name in ctx.cache}
            fresh_report = generate_pipeline_report(
                all_results, system_name=ctx.repo_path.name, llm_calls=ctx.llm_calls
            )
            _write_file(out_dir / "pipeline-report.md", fresh_report, result)
        elif synth.pipeline_report_md:
            _write_file(out_dir / "pipeline-report.md", synth.pipeline_report_md, result)
        if synth.lessons_md:
            _write_file(out_dir / "lessons.md", synth.lessons_md, result)

        # 4. Write per-system artifacts
        for sm in synth.system_models:
            sys_dir = out_dir / _slugify(sm.name)
            if sm.model_yaml:
                _write_file(sys_dir / ".architecture-model.yaml", sm.model_yaml, result)
            if sm.manifest_json:
                _write_file(sys_dir / "manifest.json", sm.manifest_json, result)
            if sm.pipeline_report_md:
                _write_file(sys_dir / "pipeline-report.md", sm.pipeline_report_md, result)
            if sm.lessons_md:
                _write_file(sys_dir / "lessons.md", sm.lessons_md, result)
            result.system_count += 1

        # 5. Write docs (system interactions from SoS model)
        if synth.sos_model and synth.sos_model.inter_system_interfaces:
            docs_dir = out_dir / "docs"
            interactions_md = _generate_system_interactions(synth)
            _write_file(docs_dir / "system-interactions.md", interactions_md, result)
            result.doc_count += 1

        # 6. Generate SE docs (non-fatal)
        self._generate_se_docs(out_dir, synth, result, diagnostics)

        # 7. Build and write test map (source→test reverse mapping)
        try:
            test_map = _build_test_map(ctx)
            if test_map:
                arch_dir = ctx.output_dir
                arch_dir.mkdir(parents=True, exist_ok=True)
                test_map_path = arch_dir / "test_map.json"
                test_map_path.write_text(json.dumps(test_map, indent=2, sort_keys=True))
                result.written_paths.append(str(test_map_path))
                result.total_bytes += test_map_path.stat().st_size

                # Build component→test aggregate if allocate data available
                alloc_result = ctx.get("allocate") if ctx.has("allocate") else None
                file_component_map: dict[str, str] = {}
                if alloc_result and alloc_result.output:
                    for comp in alloc_result.output.components:
                        for f in comp.files:
                            file_component_map[str(f)] = comp.id
                # Also check synthesize sub-results for detailed file maps
                for sm in synth.system_models:
                    sub_results = getattr(sm, "stage_results", {})
                    sub_alloc = sub_results.get("allocate")
                    if sub_alloc and hasattr(sub_alloc, "output") and sub_alloc.output:
                        for comp in sub_alloc.output.components:
                            for f in comp.files:
                                file_component_map[str(f)] = comp.id

                if file_component_map:
                    comp_test_map = _build_component_test_map(test_map, file_component_map)
                    if comp_test_map:
                        comp_map_path = arch_dir / "component_test_map.json"
                        comp_map_path.write_text(
                            json.dumps(comp_test_map, indent=2, sort_keys=True)
                        )
                        result.written_paths.append(str(comp_map_path))
                        result.total_bytes += comp_map_path.stat().st_size

                diagnostics.append(
                    Diagnostic(
                        severity="info",
                        code="TEST_MAP_BUILT",
                        message=f"Test map: {len(test_map)} source files → tests; "
                        f"{len(file_component_map)} files mapped to components",
                    )
                )
        except Exception as exc:
            diagnostics.append(
                Diagnostic(
                    severity="warning",
                    code="TEST_MAP_FAILED",
                    message=f"Test map generation failed: {exc}",
                )
            )

        duration = int((time.monotonic() - t0) * 1000)

        if not result.written_paths:
            diagnostics.append(
                Diagnostic(
                    severity="warning",
                    code="NOTHING_WRITTEN",
                    message="No artifacts written — synthesize produced empty results",
                )
            )

        quality = QualityMetrics(
            score=100.0 if result.written_paths else 0.0,
            sub_scores={
                "files_written": len(result.written_paths),
                "systems": result.system_count,
                "total_bytes": result.total_bytes,
            },
        )

        return StageResult(
            output=result,
            quality=quality,
            diagnostics=diagnostics,
            uncertainties=[],
            duration_ms=duration,
        )

    def _generate_se_docs(
        self,
        out_dir: Path,
        synth: SynthesizeResult,
        result: EmitResult,
        diagnostics: list[Diagnostic],
    ) -> None:
        """Generate SE docs for top-level and subsystem models (non-fatal)."""
        try:
            from architecture_model.core.parser import load_model
            from architecture_model.docs.se.generator import generate_se_docs
        except ImportError:
            diagnostics.append(
                Diagnostic(
                    severity="info",
                    code="SE_DOCS_UNAVAILABLE",
                    message="SE doc generator not available — skipping",
                )
            )
            return

        # Top-level SoS model
        sos_model_path = out_dir / ".architecture-model.yaml"
        if sos_model_path.exists():
            try:
                model = load_model(sos_model_path)
                se_dir = out_dir / "docs" / "se"
                se_result = generate_se_docs(model, se_dir)
                for doc_name in se_result.get("generated", []):
                    result.doc_count += 1
            except Exception as exc:
                diagnostics.append(
                    Diagnostic(
                        severity="warning",
                        code="SE_DOCS_FAILED",
                        message=f"SE doc generation failed for top-level model: {exc}",
                    )
                )

        # Per-subsystem models
        for sm in synth.system_models:
            sys_dir = out_dir / _slugify(sm.name)
            sys_model_path = sys_dir / ".architecture-model.yaml"
            if sys_model_path.exists():
                try:
                    model = load_model(sys_model_path)
                    se_dir = sys_dir / "docs" / "se"
                    se_result = generate_se_docs(model, se_dir)
                    for doc_name in se_result.get("generated", []):
                        result.doc_count += 1
                except Exception as exc:
                    diagnostics.append(
                        Diagnostic(
                            severity="warning",
                            code="SE_DOCS_FAILED",
                            message=f"SE doc generation failed for {sm.name}: {exc}",
                        )
                    )


def _generate_system_interactions(synth: SynthesizeResult) -> str:
    """Generate a system interactions doc from SoS model."""
    lines = ["# System Interactions", ""]
    if synth.sos_model:
        for iface in synth.sos_model.inter_system_interfaces:
            from_sys = iface.get("from", "?")
            to_sys = iface.get("to", "?")
            rel_type = iface.get("type", "depends-on")
            lines.append(f"- **{from_sys}** → **{to_sys}** ({rel_type})")
    if len(lines) == 2:
        lines.append("*(no inter-system interfaces detected)*")
    lines.append("")
    return "\n".join(lines)
