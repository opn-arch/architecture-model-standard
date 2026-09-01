"""Tests for pipeline history display in the HTML viewer."""

import tempfile
from pathlib import Path

import pytest

from architecture_model.core.visualize import _load_pipeline_history
from architecture_model.pipeline.history import (
    ComponentHistoryRecord,
    ModuleHistoryRecord,
    PipelineRunRecord,
    StageHistoryRecord,
    append_pipeline_history,
)


SAMPLE_REPORT = """\
# Pipeline Report: System-of-Systems

**Generated:** 2026-08-19T16:59:51Z
**Total Duration:** 6937ms
**Stages:** 8

## Stage Scores

| Stage | Score | Duration | LLM Calls |
|-------|-------|----------|-----------|
| observe | 100 | 6693ms | 0 |
| infer | 67 | 2ms | 0 |
| allocate | 75 | 0ms | 0 |
| contract | 100 | 1ms | 0 |
| relate | 100 | 241ms | 0 |
| specify | 100 | 0ms | 0 |
| decompose | 100.0 | 0ms | 0 |
| validate | 80 | 0ms | 0 |

## Stage: observe
**Score:** 100 | **Duration:** 6693ms

### Deterministic Findings
- Discovered 348 modules
- 1277 functions, 504 classes
- 635 import edges
"""


class TestLoadPipelineHistory:
    def test_returns_empty_dict_when_no_file(self, tmp_path):
        result = _load_pipeline_history(tmp_path)
        assert result == {}

    def test_returns_empty_dict_when_none(self):
        result = _load_pipeline_history(None)
        assert result == {}

    def test_parses_sample_report(self, tmp_path):
        models_dir = tmp_path / ".architecture-models"
        models_dir.mkdir()
        (models_dir / "pipeline-report.md").write_text(SAMPLE_REPORT)

        result = _load_pipeline_history(tmp_path)

        assert len(result) == 1
        assert result[0]["started_at"] == "2026-08-19T16:59:51Z"
        assert result[0]["duration_ms"] == 6937
        assert len(result[0]["stages"]) == 8
        assert result[0]["stages"][0]["name"] == "observe"

    def test_viewer_html_contains_pipeline_history(self, tmp_path):
        """When repo_path is provided with a pipeline report, viewer data includes it."""
        from architecture_model.core.parser import _parse_raw
        from architecture_model.core.visualize import generate_html_viewer

        # Minimal model
        model = _parse_raw({
            "meta": {"project": "test", "schema_version": "1.3"},
            "entities": {
                "components": [{"id": "COMP-1", "name": "Test", "status": "ACTIVE"}],
            },
            "relationships": [],
        })

        # Create pipeline report
        models_dir = tmp_path / ".architecture-models"
        models_dir.mkdir()
        (models_dir / "pipeline-report.md").write_text(SAMPLE_REPORT)

        out = tmp_path / "viewer.html"
        generate_html_viewer(model, out, repo_path=tmp_path)

        html = out.read_text()
        assert "pipeline_history" in html or "pipeline-history" in html

    def test_viewer_embeds_structured_component_and_module_history(self, tmp_path):
        from architecture_model.core.parser import _parse_raw
        from architecture_model.core.visualize import generate_html_viewer

        model = _parse_raw({
            "meta": {"project": "test", "schema_version": "1.3"},
            "entities": {"components": [{
                "id": "COMP-1", "name": "Test", "status": "ACTIVE", "files": ["src/test.py"]
            }]},
            "relationships": [],
        })
        append_pipeline_history(tmp_path, PipelineRunRecord(
            run_id="run-viewer",
            started_at="2026-09-01T12:00:00Z",
            completed_at="2026-09-01T12:00:01Z",
            duration_ms=1000,
            source="MCP",
            invocation="architect_pipeline",
            status="completed",
            produced_artifacts=[".architecture-model.yaml"],
            stages=[StageHistoryRecord(name="observe", score=100, duration_ms=25)],
            components=[ComponentHistoryRecord(
                component_id="COMP-1", name="Test", timestamp="2026-09-01T12:00:00Z",
                invoked_by="architect_pipeline", produced_entity_ids=["COMP-1"], counts={"modules": 1},
            )],
            modules=[ModuleHistoryRecord(
                path="src/test.py", module="test", component_id="COMP-1",
                timestamp="2026-09-01T12:00:00Z", invoked_by="observe",
                produced_functions=["work"], produced_entity_ids=["COMP-1"],
            )],
        ))

        out = tmp_path / "viewer.html"
        generate_html_viewer(model, out, repo_path=tmp_path)
        html = out.read_text()

        assert '"run_id": "run-viewer"' in html
        assert "renderRunHistory" in html
        assert "component_id === entityId" in html
        assert "item.path === filepath" in html
        assert "Produced Artifacts / Entities" in html
