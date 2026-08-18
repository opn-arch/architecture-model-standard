"""Tests for the emit pipeline stage."""

from __future__ import annotations

import pytest

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
        synth = SynthesizeResult(
            sos_model_yaml="meta:\n  project: test\n",
            top_manifest_json='{"modules": []}',
            pipeline_report_md="# Report\n",
            lessons_md="# Lessons\n",
            system_models=[
                SystemModel(
                    system_id="SYS-1",
                    name="Core",
                    model_yaml="meta:\n  name: core\n",
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

        assert (out_dir / ".architecture-model.yaml").exists()
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
                SystemModel(system_id="S1", name="My Component", model_yaml="x"),
                SystemModel(system_id="S2", name="FOO BAR", model_yaml="y"),
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
        content = "hello world"
        synth = SynthesizeResult(sos_model_yaml=content)
        ctx = _make_ctx(tmp_path, synth)
        result = EmitStage().run(ctx)
        assert result.output.total_bytes == len(content.encode("utf-8"))


# 10. Written paths tracking
class TestWrittenPaths:
    def test_paths(self, tmp_path):
        synth = SynthesizeResult(
            sos_model_yaml="model",
            top_manifest_json="manifest",
        )
        ctx = _make_ctx(tmp_path, synth)
        result = EmitStage().run(ctx)
        assert len(result.output.written_paths) == 2
        assert any(".architecture-model.yaml" in p for p in result.output.written_paths)
        assert any("manifest.json" in p for p in result.output.written_paths)
