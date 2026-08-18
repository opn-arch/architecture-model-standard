"""Emit pipeline stage — writes final SoS artifact structure to disk."""

from __future__ import annotations

import asyncio
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from architecture_model.pipeline.emit_types import EmitResult
from architecture_model.pipeline.protocol import (
    ArtifactReview,
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

        # 7. Build file→component map (shared by test map and requirements)
        test_map: dict[str, list[str]] = {}
        file_component_map: dict[str, str] = {}
        try:
            alloc_result = ctx.get("allocate") if ctx.has("allocate") else None
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
        except Exception:
            pass

        # 7b. Build and write test map (source→test reverse mapping)
        try:
            test_map = _build_test_map(ctx)
            if test_map:
                arch_dir = ctx.output_dir
                arch_dir.mkdir(parents=True, exist_ok=True)
                test_map_path = arch_dir / "test_map.json"
                test_map_path.write_text(json.dumps(test_map, indent=2, sort_keys=True))
                result.written_paths.append(str(test_map_path))
                result.total_bytes += test_map_path.stat().st_size

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

        # 8. Derive requirements from code signals
        try:
            from architecture_model.pipeline.requirements_derive import (
                derive_requirements,
                persist_requirements,
                select_top_requirements,
            )

            reqs = derive_requirements(ctx, file_component_map, test_map)
            if reqs:
                arch_dir = ctx.output_dir
                arch_dir.mkdir(parents=True, exist_ok=True)
                req_path = persist_requirements(reqs, arch_dir)
                result.written_paths.append(str(req_path))
                result.total_bytes += req_path.stat().st_size

                top_reqs = select_top_requirements(reqs)
                diagnostics.append(
                    Diagnostic(
                        severity="info",
                        code="REQUIREMENTS_DERIVED",
                        message=f"Derived {len(reqs)} requirements ({len(top_reqs)} promoted); "
                        f"categories: {len(set(r.category for r in reqs))}",
                    )
                )
        except Exception as exc:
            diagnostics.append(
                Diagnostic(
                    severity="warning",
                    code="REQUIREMENTS_DERIVE_FAILED",
                    message=f"Requirement derivation failed: {exc}",
                )
            )

        # 9. Enrich top-level model with pipeline-derived entities
        try:
            enrichment = _enrich_top_model(
                ctx, synth, reqs if "reqs" in dir() else [], top_reqs if "top_reqs" in dir() else []
            )
            if enrichment:
                diagnostics.append(
                    Diagnostic(
                        severity="info",
                        code="MODEL_ENRICHED",
                        message=enrichment,
                    )
                )
        except Exception as exc:
            diagnostics.append(
                Diagnostic(
                    severity="warning",
                    code="MODEL_ENRICH_FAILED",
                    message=f"Model enrichment failed: {exc}",
                )
            )

        # 10. LLM review pass on generated artifacts
        try:
            if ctx.llm_callback is not None:
                reviews = asyncio.run(self._run_llm_reviews(out_dir, ctx.llm_callback))
                inlined = _inline_reviews(out_dir, reviews)
                ctx._artifact_reviews = reviews
                diagnostics.append(
                    Diagnostic(
                        severity="info",
                        code="LLM_REVIEWS",
                        message=f"LLM reviewed {len(reviews)} artifacts, inlined into {inlined} docs",
                    )
                )
                # Regenerate artifact traceability with review data
                try:
                    from architecture_model.docs.se.artifact_traceability import (
                        generate_artifact_traceability,
                    )
                    from architecture_model.core.parser import load_model as _load_model

                    sos_model_path = out_dir / ".architecture-model.yaml"
                    if sos_model_path.exists():
                        _model = _load_model(sos_model_path)
                        trace_content = generate_artifact_traceability(
                            _model,
                            None,
                            reviews=reviews,
                            enrichments=getattr(ctx, "enrichment_log", None),
                        )
                        trace_path = out_dir / "docs" / "se" / "artifact-traceability.md"
                        trace_path.parent.mkdir(parents=True, exist_ok=True)
                        trace_path.write_text(trace_content)
                except Exception:
                    pass  # non-fatal
        except Exception as exc:
            diagnostics.append(
                Diagnostic(
                    severity="warning",
                    code="LLM_REVIEW_FAILED",
                    message=f"LLM review pass failed: {exc}",
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

    async def _run_llm_reviews(self, out_dir: Path, llm_callback) -> list[ArtifactReview]:
        """Send each reviewable artifact to LLM for review."""
        _SKIP_NAMES = {"index.md", "pipeline-report.md", "lessons.md"}
        reviews: list[ArtifactReview] = []

        # Collect reviewable files
        candidates: list[Path] = []
        for pattern in ("**/*.md", "**/*.yaml"):
            candidates.extend(out_dir.rglob(pattern.replace("**/", "")))

        for fpath in sorted(candidates):
            if fpath.name in _SKIP_NAMES:
                continue
            content = fpath.read_text(errors="replace")
            if len(content) < 50:
                continue

            rel_path = str(fpath.relative_to(out_dir))
            truncated = content[:8000]
            prompt = (
                f"Review the following architecture artifact '{rel_path}'.\n"
                f"Respond ONLY in this format:\n"
                f"SUMMARY: <one paragraph overall assessment>\n"
                f"COMMENT: <specific observation>\n"
                f"COMMENT: <another observation>\n\n"
                f"---\n{truncated}\n---"
            )

            t0 = time.monotonic()
            response = await llm_callback("review", prompt, {"artifact": rel_path})
            duration_ms = int((time.monotonic() - t0) * 1000)

            # Parse response
            summary = ""
            comments: list[str] = []
            for line in response.splitlines():
                line_s = line.strip()
                if line_s.startswith("SUMMARY:"):
                    summary = line_s[len("SUMMARY:") :].strip()
                elif line_s.startswith("COMMENT:"):
                    comments.append(line_s[len("COMMENT:") :].strip())

            reviews.append(
                ArtifactReview(
                    artifact_path=rel_path,
                    review_summary=summary,
                    comments=comments,
                    prompt_sent=prompt,
                    response_received=response,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    duration_ms=duration_ms,
                )
            )

        return reviews


def _inline_reviews(out_dir: Path, reviews: list[ArtifactReview]) -> int:
    """Append LLM Review sections to reviewed .md files. Returns count modified."""
    count = 0
    for rev in reviews:
        if not rev.artifact_path.endswith(".md"):
            continue
        fpath = out_dir / rev.artifact_path
        if not fpath.exists():
            continue

        content = fpath.read_text()

        # Strip existing LLM Review section (idempotent)
        marker = "## LLM Review"
        idx = content.find(marker)
        if idx != -1:
            # Also strip a preceding horizontal rule if present
            prefix = content[:idx].rstrip()
            if prefix.endswith("---"):
                prefix = prefix[:-3].rstrip()
            content = prefix

        # Build review section
        prompt_preview = rev.prompt_sent[:500]
        lines = [
            "",
            "---",
            "",
            "## LLM Review",
            "",
            f"*Reviewed: {rev.timestamp} | Duration: {rev.duration_ms}ms*",
            "",
            f"**Summary:** {rev.review_summary}",
            "",
        ]
        if rev.comments:
            for c in rev.comments:
                lines.append(f"- {c}")
            lines.append("")

        lines.extend(
            [
                "<details>",
                "<summary>Review details</summary>",
                "",
                "**Prompt sent (truncated):**",
                "```",
                prompt_preview,
                "```",
                "",
                "**Full LLM response:**",
                "```",
                rev.response_received,
                "```",
                "",
                "</details>",
                "",
            ]
        )

        content = content.rstrip() + "\n" + "\n".join(lines)
        fpath.write_text(content)
        count += 1

    return count


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


def _enrich_top_model(
    ctx: PipelineContext,
    synth: SynthesizeResult,
    all_reqs: list,
    top_reqs: list,
) -> str:
    """Enrich the repo's top-level .architecture-model.yaml with pipeline-derived entities.

    Merges behaviors, interfaces, actors, constraints, requirements, and
    component descriptions from pipeline stages into the existing model YAML.
    Only adds entities that don't already exist (by ID).
    """
    import yaml

    model_path = ctx.repo_path / ".architecture-model.yaml"
    if not model_path.exists():
        return ""

    model_dict = yaml.safe_load(model_path.read_text()) or {}
    entities = model_dict.setdefault("entities", {})
    relationships = model_dict.setdefault("relationships", [])

    existing_ids: set[str] = set()
    for etype in entities.values():
        if isinstance(etype, list):
            for e in etype:
                if isinstance(e, dict) and "id" in e:
                    existing_ids.add(e["id"])
    existing_rel_keys = {
        (r.get("from", ""), r.get("to", ""), r.get("type", ""))
        for r in relationships
        if isinstance(r, dict)
    }

    added: dict[str, int] = {}

    # 1. Behaviors from infer stage
    infer_result = ctx.get("infer") if ctx.has("infer") else None
    if infer_result and infer_result.output and hasattr(infer_result.output, "behaviors"):
        behaviors = entities.setdefault("behaviors", [])
        for beh in infer_result.output.behaviors:
            if beh.id not in existing_ids:
                beh_dict = {"id": beh.id, "name": beh.name}
                if beh.behavior_type:
                    beh_dict["behavior_type"] = beh.behavior_type
                if beh.steps:
                    beh_dict["steps"] = beh.steps
                if beh.actor_id:
                    beh_dict["actor_id"] = beh.actor_id
                if beh.triggers:
                    beh_dict["triggers"] = beh.triggers
                if beh.capability_id:
                    beh_dict["capability_id"] = beh.capability_id
                behaviors.append(beh_dict)
                existing_ids.add(beh.id)
                added["behaviors"] = added.get("behaviors", 0) + 1

    # 2. Actors from infer stage
    if infer_result and infer_result.output and hasattr(infer_result.output, "actors"):
        actors = entities.setdefault("actors", [])
        for actor in infer_result.output.actors:
            if actor.id not in existing_ids:
                actor_dict = {"id": actor.id, "name": actor.name}
                if actor.actor_type:
                    actor_dict["actor_type"] = actor.actor_type
                # Add default goal based on actor type
                if actor.actor_type == "human":
                    actor_dict["goals"] = [f"Use {ctx.repo_path.name} effectively"]
                elif actor.actor_type == "system":
                    actor_dict["goals"] = [f"Integrate with {ctx.repo_path.name}"]
                else:
                    actor_dict["goals"] = [f"Interact with {ctx.repo_path.name}"]
                actors.append(actor_dict)
                existing_ids.add(actor.id)
                added["actors"] = added.get("actors", 0) + 1
        # Ensure existing actors have goals
        for actor in actors:
            if isinstance(actor, dict) and not actor.get("goals") and not actor.get("description"):
                actor["goals"] = [f"Interact with {ctx.repo_path.name}"]

    # 3. Interfaces from specify stage
    specify_result = ctx.get("specify") if ctx.has("specify") else None
    if specify_result and specify_result.output and hasattr(specify_result.output, "interfaces"):
        interfaces = entities.setdefault("interfaces", [])
        for iface in specify_result.output.interfaces:
            if iface.id not in existing_ids:
                iface_dict = {
                    "id": iface.id,
                    "name": iface.name,
                    "interface_type": iface.interface_type,
                }
                if iface.component_id:
                    iface_dict["component_id"] = iface.component_id
                if iface.methods:
                    iface_dict["methods"] = iface.methods
                if iface.description:
                    iface_dict["description"] = iface.description
                interfaces.append(iface_dict)
                existing_ids.add(iface.id)
                added["interfaces"] = added.get("interfaces", 0) + 1

    # 4. Constraints from observe stage
    observe_result = ctx.get("observe") if ctx.has("observe") else None
    if observe_result and observe_result.output and hasattr(observe_result.output, "constraints"):
        constraints = entities.setdefault("constraints", [])
        for i, con in enumerate(observe_result.output.constraints):
            con_id = f"CON-{i + 1}"
            if con_id not in existing_ids:
                con_dict = {"id": con_id, "name": con.name, "value": con.value}
                if con.constraint_type:
                    con_dict["constraint_type"] = con.constraint_type
                constraints.append(con_dict)
                existing_ids.add(con_id)
                added["constraints"] = added.get("constraints", 0) + 1

    # 5. Requirements from derivation
    if top_reqs:
        requirements = entities.setdefault("requirements", [])
        for req in top_reqs:
            if req.id not in existing_ids:
                requirements.append(
                    {
                        "id": req.id,
                        "name": req.name,
                        "category": req.category,
                        "priority": req.priority,
                    }
                )
                existing_ids.add(req.id)
                added["requirements"] = added.get("requirements", 0) + 1

    # 6. Component descriptions from allocate stage
    alloc_result = ctx.get("allocate") if ctx.has("allocate") else None
    comp_ids = set()
    file_to_comp: dict[str, str] = {}
    if alloc_result and alloc_result.output and hasattr(alloc_result.output, "components"):
        alloc_comp_map = {c.id: c for c in alloc_result.output.components}
        for ac in alloc_result.output.components:
            for f in ac.files:
                file_to_comp[str(f)] = ac.id
        components = entities.get("components", [])
        desc_count = 0
        for comp in components:
            if isinstance(comp, dict):
                comp_ids.add(comp.get("id", ""))
            if isinstance(comp, dict) and not comp.get("description"):
                cid = comp.get("id", "")
                alloc_comp = alloc_comp_map.get(cid)
                if alloc_comp and getattr(alloc_comp, "description", None):
                    comp["description"] = alloc_comp.description
                    desc_count += 1
                elif alloc_comp and getattr(alloc_comp, "files", None):
                    # Build description from directory structure
                    dirs = sorted(set(str(Path(f).parent) for f in alloc_comp.files))[:3]
                    comp["description"] = (
                        f"Source in {', '.join(dirs)} ({len(alloc_comp.files)} files)"
                    )
                    desc_count += 1
                elif comp.get("files"):
                    # Use files from the model itself
                    files = comp["files"]
                    dirs = sorted(set(str(Path(f).parent) for f in files))[:3]
                    comp["description"] = f"Source in {', '.join(dirs)} ({len(files)} files)"
                    desc_count += 1
                elif comp.get("name"):
                    # Last resort: use component name
                    comp["description"] = f"Handles {comp['name'].lower()} functionality"
                    desc_count += 1
            # Also handle children
            for child in comp.get("children", []) if isinstance(comp, dict) else []:
                if isinstance(child, dict) and not child.get("description"):
                    child_cid = child.get("id", "")
                    alloc_child = alloc_comp_map.get(child_cid)
                    if alloc_child and getattr(alloc_child, "files", None):
                        dirs = sorted(set(str(Path(f).parent) for f in alloc_child.files))[:3]
                        child["description"] = (
                            f"Source in {', '.join(dirs)} ({len(alloc_child.files)} files)"
                        )
                        desc_count += 1
                    elif child.get("files"):
                        files = child["files"]
                        dirs = sorted(set(str(Path(f).parent) for f in files))[:3]
                        child["description"] = f"Source in {', '.join(dirs)} ({len(files)} files)"
                        desc_count += 1
                    elif child.get("name"):
                        child["description"] = f"Handles {child['name'].lower()} functionality"
                        desc_count += 1
                    elif alloc_comp and getattr(alloc_comp, "files", None):
                        # Build description from directory structure
                        dirs = sorted(set(str(Path(f).parent) for f in alloc_comp.files))[:3]
                        comp["description"] = (
                            f"Source in {', '.join(dirs)} ({len(alloc_comp.files)} files)"
                        )
                        desc_count += 1
                # Also handle children
                for child in comp.get("children", []):
                    if isinstance(child, dict):
                        comp_ids.add(child.get("id", ""))
        if desc_count:
            added["descriptions"] = desc_count
    else:
        # Collect comp_ids from entities directly
        for comp in entities.get("components", []):
            if isinstance(comp, dict):
                comp_ids.add(comp.get("id", ""))
                for child in comp.get("children", []):
                    if isinstance(child, dict):
                        comp_ids.add(child.get("id", ""))

    # Helper to resolve sub-component IDs to known comp_ids
    def _resolve_comp(cid: str) -> str:
        """Resolve a sub-component ID to a known comp_id (strip suffix if needed)."""
        if cid in comp_ids:
            return cid
        # Try parent: COMP-5-1 → COMP-5
        parts = cid.rsplit("-", 1)
        if len(parts) == 2 and parts[0] in comp_ids:
            return parts[0]
        return ""

    # 7. Create linking relationships
    rel_count = 0

    # Build route→component map from observe stage
    route_comp_map: dict[str, str] = {}  # behavior_name → component_id
    if observe_result and observe_result.output and hasattr(observe_result.output, "routes"):
        for route in observe_result.output.routes or []:
            route_name = (
                f"{route.method} {route.path}" if hasattr(route, "method") else str(route.path)
            )
            comp = file_to_comp.get(str(route.file), "")
            resolved = _resolve_comp(comp) if comp else ""
            if resolved:
                route_comp_map[route_name] = resolved

    # 7a. Behaviors → Components: link via steps, capability, or route name
    for beh in entities.get("behaviors", []):
        if not isinstance(beh, dict):
            continue
        beh_id = beh.get("id", "")
        beh_name = beh.get("name", "")
        linked_comps: set[str] = set()

        # Method 1: component IDs in steps
        for step in beh.get("steps", []):
            step_str = str(step)
            for cid in comp_ids:
                if cid in step_str:
                    linked_comps.add(cid)

        # Method 2: route name match
        if not linked_comps and beh_name in route_comp_map:
            linked_comps.add(route_comp_map[beh_name])

        # Method 3: capability_id → find components that realize this capability
        if not linked_comps and beh.get("capability_id"):
            for rel in relationships:
                if (
                    isinstance(rel, dict)
                    and rel.get("type") == "realizes"
                    and rel.get("to") == beh.get("capability_id")
                ):
                    linked_comps.add(rel.get("from", ""))

        for cid in linked_comps:
            resolved_cid = _resolve_comp(cid)
            key = (beh_id, resolved_cid, "realizes")
            if resolved_cid and key not in existing_rel_keys:
                relationships.append({"from": beh_id, "to": resolved_cid, "type": "realizes"})
                existing_rel_keys.add(key)
                rel_count += 1

    # 7b. Requirements → Components: link by component_id from derivation
    if top_reqs:
        for req in top_reqs:
            resolved = _resolve_comp(req.component_id) if req.component_id else ""
            if resolved:
                key = (resolved, req.id, "satisfies")
                if key not in existing_rel_keys:
                    relationships.append({"from": resolved, "to": req.id, "type": "satisfies"})
                    existing_rel_keys.add(key)
                    rel_count += 1
        # Also link requirements without component_id via source file
        if file_to_comp:
            for req in top_reqs:
                resolved = _resolve_comp(req.component_id) if req.component_id else ""
                if not resolved and req.source_file:
                    raw_comp = file_to_comp.get(req.source_file, "")
                    comp = _resolve_comp(raw_comp) if raw_comp else ""
                    if comp:
                        key = (comp, req.id, "satisfies")
                        if key not in existing_rel_keys:
                            relationships.append({"from": comp, "to": req.id, "type": "satisfies"})
                            existing_rel_keys.add(key)
                            rel_count += 1

    # 7c. Interfaces → Components: create exposes relationship
    for iface in entities.get("interfaces", []):
        if isinstance(iface, dict) and iface.get("component_id"):
            iface_comp = _resolve_comp(iface["component_id"])
            if iface_comp:
                key = (iface_comp, iface.get("id", ""), "exposes")
                if key not in existing_rel_keys:
                    relationships.append({"from": iface_comp, "to": iface["id"], "type": "exposes"})
                    existing_rel_keys.add(key)
                    rel_count += 1

    if rel_count:
        added["relationships"] = rel_count

    if not added:
        return ""

    # Write enriched model
    model_path.write_text(yaml.dump(model_dict, default_flow_style=False, sort_keys=False))
    parts = [f"{k}: +{v}" for k, v in sorted(added.items())]
    return f"Top-level model enriched: {', '.join(parts)}"
