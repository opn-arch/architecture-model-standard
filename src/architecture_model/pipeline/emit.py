"""Emit pipeline stage — writes final SoS artifact structure to disk."""
from __future__ import annotations

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

        # 3. Write top-level reports
        if synth.pipeline_report_md:
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
