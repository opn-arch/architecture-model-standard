"""Tests for the emit pipeline stage."""

from __future__ import annotations

import pytest
import yaml
from pathlib import Path
import os

from architecture_model.pipeline.emit import EmitStage, _slugify
from architecture_model.pipeline.emit_types import EmitResult
from architecture_model.pipeline.protocol import PipelineContext, QualityMetrics, StageResult
from architecture_model.pipeline.synthesize_types import SoSModel, SynthesizeResult, SystemModel


def _make_ctx(tmp_path, synth_result):
    ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path)
    ctx.cache["synthesize"] = StageResult(
        output=synth_result,
        quality=QualityMetrics(score=100.0),
        diagnostics=[],
        uncertainties=[],
    )
    return ctx


def _model(project="test", entities=None, relationships=None):
    return yaml.safe_dump({
        "meta": {
            "project": project,
            "schema_version": "2.0.0",
            "generated_at": "2026-09-01T00:00:00Z",
            "source_artifacts": ["source.py"],
        },
        "entities": entities or {},
        "relationships": relationships or [],
    }, sort_keys=False)


# 1. EmitResult defaults
class TestEmitResultDefaults:
    def test_defaults(self):
        r = EmitResult()
        assert r.written_paths == []
        assert r.total_bytes == 0
        assert r.system_count == 0
        assert r.doc_count == 0
        assert r.output_dir == ""


# 2. _slugify
class TestSlugify:
    @pytest.mark.parametrize(
        "inp,expected",
        [
            ("Core", "core"),
            ("My Component", "my-component"),
            ("FOO_BAR", "foo-bar"),
            ("hello world!!", "hello-world"),
            ("a--b", "a-b"),
            ("  spaces  ", "spaces"),
        ],
    )
    def test_slugify(self, inp, expected):
        assert _slugify(inp) == expected


# 3. EmitStage metadata
class TestEmitStageMeta:
    def test_name_version_requires(self):
        s = EmitStage()
        assert s.name == "emit"
        assert s.version == "1.0"
        assert s.requires == ["synthesize"]

    def test_can_run_true(self, tmp_path):
        ctx = _make_ctx(tmp_path, SynthesizeResult())
        assert EmitStage().can_run(ctx) is True

    def test_can_run_false(self, tmp_path):
        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path)
        assert EmitStage().can_run(ctx) is False


# 4. Full run with all artifacts
class TestEmitRunFull:
    def test_full_run(self, tmp_path):
        sub_path = ".architecture-models/core/.architecture-model.yaml"
        synth = SynthesizeResult(
            sos_model_yaml=_model(entities={"systems": [{
                "id": "SYS-1", "name": "Core", "status": "ACTIVE",
                "sub_model_ref": sub_path,
            }]}),
            top_manifest_json='{"modules": []}',
            pipeline_report_md="# Report\n",
            lessons_md="# Lessons\n",
            system_models=[
                SystemModel(
                    system_id="SYS-1",
                    name="Core",
                    model_yaml=_model(project="core"),
                    manifest_json='{"files": []}',
                    pipeline_report_md="# Core Report\n",
                    lessons_md="# Core Lessons\n",
                ),
            ],
            sos_model=SoSModel(
                inter_system_interfaces=[
                    {"from": "Core", "to": "Manifest", "type": "depends-on"},
                ],
            ),
        )
        ctx = _make_ctx(tmp_path, synth)
        result = EmitStage().run(ctx)
        out = result.output
        out_dir = tmp_path / ".architecture-models"

        assert (tmp_path / ".architecture-model.yaml").exists()
        assert (out_dir / "manifest.json").exists()
        assert (out_dir / "pipeline-report.md").exists()
        assert (out_dir / "lessons.md").exists()
        assert (out_dir / "core" / ".architecture-model.yaml").exists()
        assert (out_dir / "core" / "manifest.json").exists()
        assert (out_dir / "core" / "pipeline-report.md").exists()
        assert (out_dir / "core" / "lessons.md").exists()
        assert (out_dir / "docs" / "system-interactions.md").exists()
        assert out.system_count == 1
        assert out.doc_count >= 1
        assert len(out.written_paths) >= 9
        assert result.quality.score == 100.0
        assert out.promoted is True
        assert out.final_model_path == str(tmp_path / ".architecture-model.yaml")
        assert out.final_model_score > 0
        assert out.extraction_score == 0

    def test_reports_extraction_and_final_validation_separately(self, tmp_path):
        synth = SynthesizeResult(sos_model_yaml=_model())
        ctx = _make_ctx(tmp_path, synth)
        ctx.cache["validate"] = StageResult(
            output=None, quality=QualityMetrics(score=95), diagnostics=[], uncertainties=[]
        )

        result = EmitStage().run(ctx)

        assert result.output.extraction_score == 95
        assert result.output.final_model_score == 100
        assert result.quality.sub_scores["extraction_score"] == 95
        assert result.quality.sub_scores["final_model_score"] == 100
        assert result.quality.sub_scores["promoted"] == 100
        report = (tmp_path / ".architecture-models" / "pipeline-report.md").read_text()
        assert "**Extraction Score:** 95" in report
        assert "**Final Model Score:** 100" in report
        assert "**Promoted:** yes" in report


# 5. Empty SynthesizeResult
class TestEmitRunEmpty:
    def test_empty_synth(self, tmp_path):
        ctx = _make_ctx(tmp_path, SynthesizeResult())
        result = EmitStage().run(ctx)
        assert result.output.written_paths == []
        assert len(result.diagnostics) == 1
        assert result.diagnostics[0].code == "NOTHING_WRITTEN"
        assert result.quality.score == 0.0


# 6. Per-system slugified dirs
class TestPerSystemDirs:
    def test_slugified_names(self, tmp_path):
        synth = SynthesizeResult(
            system_models=[
                SystemModel(system_id="S1", name="My Component", model_yaml=_model()),
                SystemModel(system_id="S2", name="FOO BAR", model_yaml=_model()),
            ],
        )
        ctx = _make_ctx(tmp_path, synth)
        EmitStage().run(ctx)
        out_dir = tmp_path / ".architecture-models"
        assert (out_dir / "my-component" / ".architecture-model.yaml").exists()
        assert (out_dir / "foo-bar" / ".architecture-model.yaml").exists()


# 7. Reports at both levels
class TestReportsAtBothLevels:
    def test_reports(self, tmp_path):
        synth = SynthesizeResult(
            pipeline_report_md="top report",
            lessons_md="top lessons",
            system_models=[
                SystemModel(
                    system_id="S1",
                    name="sub",
                    pipeline_report_md="sub report",
                    lessons_md="sub lessons",
                ),
            ],
        )
        ctx = _make_ctx(tmp_path, synth)
        EmitStage().run(ctx)
        out_dir = tmp_path / ".architecture-models"
        assert (out_dir / "pipeline-report.md").read_text() == "top report"
        assert (out_dir / "lessons.md").read_text() == "top lessons"
        assert (out_dir / "sub" / "pipeline-report.md").read_text() == "sub report"
        assert (out_dir / "sub" / "lessons.md").read_text() == "sub lessons"


# 8. System interactions doc
class TestSystemInteractions:
    def test_generated(self, tmp_path):
        synth = SynthesizeResult(
            sos_model=SoSModel(
                inter_system_interfaces=[
                    {"from": "A", "to": "B", "type": "exposes"},
                ],
            ),
        )
        ctx = _make_ctx(tmp_path, synth)
        EmitStage().run(ctx)
        doc = (tmp_path / ".architecture-models" / "docs" / "system-interactions.md").read_text()
        assert "**A**" in doc
        assert "**B**" in doc
        assert "exposes" in doc

    def test_not_generated_without_interfaces(self, tmp_path):
        synth = SynthesizeResult(sos_model=SoSModel())
        ctx = _make_ctx(tmp_path, synth)
        EmitStage().run(ctx)
        assert not (tmp_path / ".architecture-models" / "docs").exists()


# 9. Total bytes tracking
class TestTotalBytes:
    def test_bytes(self, tmp_path):
        content = _model()
        synth = SynthesizeResult(sos_model_yaml=content)
        ctx = _make_ctx(tmp_path, synth)
        result = EmitStage().run(ctx)
        assert result.output.total_bytes == len(content.encode("utf-8"))


# 10. Written paths tracking
class TestWrittenPaths:
    def test_paths(self, tmp_path):
        synth = SynthesizeResult(
            sos_model_yaml=_model(),
            top_manifest_json="manifest",
        )
        ctx = _make_ctx(tmp_path, synth)
        result = EmitStage().run(ctx)
        assert len(result.output.written_paths) == 3
        assert any(".architecture-model.yaml" in p for p in result.output.written_paths)
        assert any("manifest.json" in p for p in result.output.written_paths)

    def test_invalid_candidate_preserves_existing_canonical_model(self, tmp_path):
        canonical = tmp_path / ".architecture-model.yaml"
        canonical.write_text(_model(project="existing"))
        synth = SynthesizeResult(sos_model_yaml="meta:\n  project: ''\n")

        result = EmitStage().run(_make_ctx(tmp_path, synth))

        assert yaml.safe_load(canonical.read_text())["meta"]["project"] == "existing"
        assert result.output.promoted is False
        assert result.output.final_validation_issues
        assert Path(result.output.candidate_path).exists()
        assert result.quality.score == result.output.final_model_score

    def test_transaction_rolls_back_root_and_subsystem_on_second_replace_failure(
        self, tmp_path, monkeypatch
    ):
        root = tmp_path / ".architecture-model.yaml"
        subsystem = tmp_path / ".architecture-models" / "core" / ".architecture-model.yaml"
        subsystem.parent.mkdir(parents=True)
        old_root = _model(project="old-root").encode()
        old_subsystem = _model(project="old-core").encode()
        root.write_bytes(old_root)
        subsystem.write_bytes(old_subsystem)
        synth = SynthesizeResult(
            sos_model_yaml=_model(entities={"systems": [{
                "id": "SYS-1", "name": "Core", "status": "ACTIVE",
                "sub_model_ref": ".architecture-models/core/.architecture-model.yaml",
            }]}),
            system_models=[SystemModel(
                system_id="SYS-1", name="Core", model_yaml=_model(project="new-core")
            )],
        )
        real_replace = os.replace
        candidate_replacements = 0

        def fail_second_candidate(source, target):
            nonlocal candidate_replacements
            if ".architecture-model-candidates" in str(source):
                candidate_replacements += 1
                if candidate_replacements == 2:
                    raise OSError("injected second replacement failure")
            return real_replace(source, target)

        monkeypatch.setattr("architecture_model.pipeline.emit.os.replace", fail_second_candidate)

        result = EmitStage().run(_make_ctx(tmp_path, synth))

        assert result.output.promoted is False
        assert root.read_bytes() == old_root
        assert subsystem.read_bytes() == old_subsystem
        assert not list(tmp_path.rglob("*.architecture-backup"))

    def test_structural_warning_for_dangling_reference_blocks_promotion(self, tmp_path):
        canonical = tmp_path / ".architecture-model.yaml"
        canonical.write_text(_model(project="existing"))
        invalid = _model(
            entities={"capabilities": [{"id": "CAP-1", "name": "Cap", "status": "ACTIVE"}]},
            relationships=[{"from": "CAP-1", "to": "CAP-MISSING", "type": "depends-on"}],
        )

        result = EmitStage().run(_make_ctx(tmp_path, SynthesizeResult(sos_model_yaml=invalid)))

        assert result.output.promoted is False
        assert yaml.safe_load(canonical.read_text())["meta"]["project"] == "existing"
        assert any(issue["code"] == "STRUCTURAL_DANGLING_REF" for issue in result.output.final_validation_issues)

    @pytest.mark.parametrize(
        "entities",
        [
            {
                "components": [{"id": "COMP-1", "name": "Comp", "status": "ACTIVE"}],
                "behaviors": [{
                    "id": "BEH-1", "name": "Flow", "status": "ACTIVE",
                    "structured_steps": [{"order": 1, "action": "Run", "component_ref": "COMP-MISSING"}],
                }],
            },
            {
                "capabilities": [{"id": "CAP-1", "name": "Cap", "status": "ACTIVE"}],
                "behaviors": [{
                    "id": "BEH-1", "name": "Flow", "status": "ACTIVE",
                    "capability_id": "CAP-MISSING",
                }],
            },
            {
                "interfaces": [{
                    "id": "IF-1", "name": "API", "status": "ACTIVE",
                    "type": "internal", "provider": "COMP-MISSING",
                }],
            },
            {
                "components": [{
                    "id": "COMP-1", "name": "Comp", "status": "ACTIVE",
                    "interfaces": [{
                        "name": "dependency", "kind": "requires",
                        "target_component": "COMP-MISSING",
                    }],
                }],
            },
        ],
    )
    def test_embedded_dangling_references_block_promotion(self, tmp_path, entities):
        canonical = tmp_path / ".architecture-model.yaml"
        canonical.write_text(_model(project="existing"))

        result = EmitStage().run(_make_ctx(
            tmp_path, SynthesizeResult(sos_model_yaml=_model(entities=entities)),
        ))

        assert result.output.promoted is False
        assert any(
            issue["code"] == "STRUCTURAL_DANGLING_REF"
            for issue in result.output.final_validation_issues
        )

    def test_inline_requirement_statements_and_contract_names_can_promote(self, tmp_path):
        entities = {
            "components": [{
                "id": "COMP-1", "name": "Comp", "status": "ACTIVE",
                "requirements": ["Must remain available"],
                "interface_refs": ["Python call contract"],
            }],
        }

        result = EmitStage().run(_make_ctx(
            tmp_path, SynthesizeResult(sos_model_yaml=_model(entities=entities)),
        ))

        assert result.output.promoted is True

    def test_candidate_enrichment_defect_is_validated_before_promotion(self, tmp_path):
        canonical = tmp_path / ".architecture-model.yaml"
        old_bytes = _model(project="existing").encode()
        canonical.write_bytes(old_bytes)
        ctx = _make_ctx(tmp_path, SynthesizeResult(sos_model_yaml=_model(project="candidate")))

        def invalid_enrichment(path, _ctx, _synth):
            raw = yaml.safe_load(path.read_text())
            raw["relationships"] = [{"from": "CAP-1", "to": "CAP-MISSING", "type": "depends-on"}]
            path.write_text(yaml.safe_dump(raw))

        ctx.config["final_model_enricher"] = invalid_enrichment

        result = EmitStage().run(ctx)

        assert result.output.promoted is False
        assert canonical.read_bytes() == old_bytes
        assert "CAP-MISSING" in Path(result.output.candidate_path).read_text()
