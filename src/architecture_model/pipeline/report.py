"""Pipeline report generator — markdown summary of a pipeline run."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .protocol import Diagnostic, LLMCallRecord, StageResult, Uncertainty


@dataclass
class StageReport:
    """Renderable report for a single pipeline stage."""

    stage_name: str
    duration_ms: int
    score: float
    deterministic_findings: list[str] = field(default_factory=list)
    llm_calls: list[LLMCallRecord] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)
    uncertainties: list[Uncertainty] = field(default_factory=list)

    def to_markdown(self) -> str:
        lines: list[str] = []
        lines.append(f"## Stage: {self.stage_name}")
        lines.append(f"**Score:** {self.score} | **Duration:** {self.duration_ms}ms")
        lines.append("")

        lines.append("### Deterministic Findings")
        if self.deterministic_findings:
            for f in self.deterministic_findings:
                lines.append(f"- {f}")
        else:
            lines.append("*(none)*")
        lines.append("")

        if self.llm_calls:
            lines.append(f"### LLM Calls ({len(self.llm_calls)})")
            lines.append("")
            for i, call in enumerate(self.llm_calls, 1):
                lines.append(
                    f"#### {i}. {call.purpose} ({call.duration_ms:,}ms)"
                )
                if call.model:
                    lines.append(f"- **Model:** {call.model}")
                if call.files_sent:
                    files = ", ".join(f"`{f}`" for f in call.files_sent)
                    lines.append(f"- **Files sent:** {files}")
                if call.slices_sent:
                    lines.append(f"- **Slices:** {', '.join(call.slices_sent)}")
                lines.append(
                    f"- **Tokens:** {call.prompt_tokens:,} prompt"
                    f" ({call.context_tokens:,} context)"
                    f" → {call.completion_tokens:,} completion"
                    f" = {call.total_tokens:,} total"
                )
                parts: list[str] = []
                if call.items_produced:
                    parts.append(f"{call.items_produced} items produced")
                if call.confidence:
                    parts.append(f"confidence: {call.confidence:.2f}")
                if parts:
                    lines.append(f"- **Result:** {' ('.join(parts)}{')'  if len(parts) > 1 else ''}")
                if call.cached:
                    lines.append("- **Cached:** yes")
                lines.append("")
        else:
            lines.append("### LLM Calls")
            lines.append("*(none)*")
            lines.append("")

        lines.append("### Diagnostics")
        if self.diagnostics:
            for d in self.diagnostics:
                icon = {"warning": "⚠️", "error": "❌", "info": "ℹ️"}.get(
                    d.severity, "•"
                )
                lines.append(f"- {icon} {d.code}: {d.message}")
        else:
            lines.append("*(none)*")
        lines.append("")

        if self.uncertainties:
            lines.append("### Uncertainties")
            for u in self.uncertainties:
                lines.append(f"- {u.category}: {u.description}")
            lines.append("")

        return "\n".join(lines)


def _extract_findings(stage_name: str, result: StageResult) -> list[str]:
    """Extract human-readable findings from a stage's output type."""
    output = result.output
    if output is None:
        return []

    findings: list[str] = []

    if stage_name == "observe":
        try:
            from .observe_types import Inventory

            if isinstance(output, Inventory):
                findings.append(f"Discovered {len(output.modules)} modules")
                fn_count = sum(len(m.functions) for m in output.modules)
                cls_count = sum(len(m.classes) for m in output.modules)
                findings.append(f"{fn_count} functions, {cls_count} classes")
                findings.append(f"{len(output.edges)} import edges")
        except ImportError:
            pass

    elif stage_name == "infer":
        try:
            from .infer_types import InferenceResult

            if isinstance(output, InferenceResult):
                findings.append(f"Inferred {len(output.capabilities)} capabilities")
                findings.append(f"{len(output.actors)} actors")
                findings.append(f"{len(output.behaviors)} behaviors")
        except ImportError:
            pass

    elif stage_name == "allocate":
        try:
            from .allocate_types import AllocationResult

            if isinstance(output, AllocationResult):
                findings.append(f"{len(output.components)} components")
                findings.append(f"File coverage: {output.file_coverage:.0f}%")
                findings.append(f"{len(output.unallocated)} unallocated files")
        except ImportError:
            pass

    elif stage_name == "relate":
        try:
            from .relate_types import RelateResult

            if isinstance(output, RelateResult):
                type_counts = Counter(r.rel_type for r in output.relationships)
                for rtype, count in type_counts.most_common():
                    findings.append(f"{count} {rtype} relationships")
        except ImportError:
            pass

    elif stage_name == "specify":
        try:
            from .specify_types import SpecifyResult

            if isinstance(output, SpecifyResult):
                findings.append(f"{len(output.interfaces)} interfaces")
        except ImportError:
            pass

    elif stage_name == "contract":
        try:
            from .contract_types import ContractResult

            if isinstance(output, ContractResult):
                findings.append(f"{len(output.contracts)} contracts")
        except ImportError:
            pass

    elif stage_name == "validate":
        try:
            from .validate_types import ValidateResult

            if isinstance(output, ValidateResult):
                findings.append(f"Score: {output.score}/100")
                findings.append(f"{len(output.issues)} issues")
        except ImportError:
            pass

    elif stage_name == "decompose":
        try:
            from .decompose_types import DecomposeResult

            if isinstance(output, DecomposeResult):
                findings.append(f"{len(output.systems)} systems")
                findings.append(f"{len(output.inline_components)} inline components")
                findings.append(
                    f"{len(output.inter_system_edges)} inter-system edges"
                )
        except ImportError:
            pass

    return findings


def generate_pipeline_report(
    results: dict[str, StageResult],
    system_name: str = "System",
    llm_calls: list[LLMCallRecord] | None = None,
) -> str:
    """Generate a complete markdown pipeline report."""
    llm_calls = llm_calls or []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    total_duration = sum(r.duration_ms for r in results.values())

    lines: list[str] = []
    lines.append(f"# Pipeline Report: {system_name}")
    lines.append("")
    lines.append(f"**Generated:** {now}")
    lines.append(f"**Total Duration:** {total_duration}ms")
    lines.append(f"**Stages:** {len(results)}")
    emit_result = results.get("emit")
    if emit_result and hasattr(emit_result.output, "final_model_score"):
        emitted = emit_result.output
        lines.append(f"**Extraction Score:** {emitted.extraction_score:g}")
        lines.append(f"**Final Model Score:** {emitted.final_model_score:g}")
        if emitted.final_model_path:
            lines.append(f"**Final Model:** `{emitted.final_model_path}`")
        lines.append(f"**Promoted:** {'yes' if emitted.promoted else 'no'}")
        if emitted.final_validation_issues:
            lines.append(f"**Final Validation Issues:** {len(emitted.final_validation_issues)}")
    lines.append("")

    # LLM Summary
    lines.append("## LLM Summary")
    lines.append("")
    if llm_calls:
        total_prompt = sum(c.prompt_tokens for c in llm_calls)
        total_completion = sum(c.completion_tokens for c in llm_calls)
        total_tokens = sum(c.total_tokens for c in llm_calls)
        models = sorted({c.model for c in llm_calls if c.model})
        cache_hits = sum(1 for c in llm_calls if c.cached)
        total_llm_dur = sum(c.duration_ms for c in llm_calls)

        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Total Calls | {len(llm_calls)} |")
        lines.append(
            f"| Total Tokens | {total_tokens:,}"
            f" (prompt: {total_prompt:,}, completion: {total_completion:,}) |"
        )
        lines.append(f"| Models Used | {', '.join(models) if models else 'unknown'} |")
        lines.append(f"| Cache Hits | {cache_hits}/{len(llm_calls)} |")
        lines.append(f"| Total LLM Duration | {total_llm_dur:,}ms |")
    else:
        lines.append("No LLM calls — deterministic pipeline run")
    lines.append("")

    # Stage scores table
    lines.append("## Stage Scores")
    lines.append("")
    lines.append("| Stage | Score | Duration | LLM Calls |")
    lines.append("|-------|-------|----------|-----------|")
    calls_by_stage: dict[str, list[LLMCallRecord]] = {}
    for c in llm_calls:
        calls_by_stage.setdefault(c.stage, []).append(c)
    for name, result in results.items():
        n_calls = len(calls_by_stage.get(name, []))
        lines.append(
            f"| {name} | {result.quality.score} | {result.duration_ms}ms | {n_calls} |"
        )
    lines.append("")

    # Per-stage detail
    for name, result in results.items():
        stage_calls = calls_by_stage.get(name, [])
        findings = _extract_findings(name, result)
        sr = StageReport(
            stage_name=name,
            duration_ms=result.duration_ms,
            score=result.quality.score,
            deterministic_findings=findings,
            llm_calls=stage_calls,
            diagnostics=result.diagnostics,
            uncertainties=result.uncertainties,
        )
        lines.append(sr.to_markdown())

    return "\n".join(lines)
