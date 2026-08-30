"""Tests for llm_refine module."""

import asyncio
import json

import pytest

from architecture_model.pipeline.llm_refine import (
    RefinementLog,
    _LLM_REFINABLE_STAGES,
    apply_additions_infer,
    apply_additions_relate,
    apply_layer_corrections,
    apply_renames,
    normalize_llm_output,
    refine_with_llm,
)
from architecture_model.pipeline.infer_types import (
    InferenceResult,
    InferredBehavior,
    InferredCapability,
)
from architecture_model.pipeline.allocate_types import AllocationResult, ComponentAllocation
from architecture_model.pipeline.relate_types import DerivedRelationship, RelateResult
from architecture_model.pipeline.specify_types import InterfaceSpec, SpecifyResult
from architecture_model.pipeline.protocol import QualityMetrics, StageResult


# ── normalize_llm_output ────────────────────────────────────────────────


class TestNormalizeInfer:
    def test_basic(self):
        raw = {
            "capabilities": [{"name": "Auth", "source_file": "auth.py"}],
            "behaviors": [{"name": "Login", "type": "use_case"}],
        }
        out = normalize_llm_output("infer", raw)
        assert len(out["capabilities"]) == 1
        assert out["capabilities"][0]["name"] == "Auth"
        assert out["capabilities"][0]["source_files"] == ["auth.py"]
        assert out["capabilities"][0]["id"] == "CAP-F1"
        assert len(out["behaviors"]) == 1
        assert out["actors"] == []

    def test_missing_fields(self):
        out = normalize_llm_output("infer", {})
        assert out == {"capabilities": [], "actors": [], "behaviors": []}


class TestNormalizeAllocate:
    def test_basic(self):
        raw = {"components": [{"name": "Web", "files": ["a.py"], "layer": "web", "capability_id": "CAP-F1"}]}
        out = normalize_llm_output("allocate", raw)
        assert out["components"][0]["layer"] == "web"
        assert out["components"][0]["files"] == ["a.py"]

    def test_files_as_string(self):
        raw = {"components": [{"name": "X", "files": "single.py"}]}
        out = normalize_llm_output("allocate", raw)
        assert out["components"][0]["files"] == ["single.py"]


class TestNormalizeRelate:
    def test_basic(self):
        raw = {"relationships": [{"from": "COMP-1", "to": "CAP-F1", "type": "realizes"}]}
        out = normalize_llm_output("relate", raw)
        assert out["relationships"][0] == {"from_id": "COMP-1", "to_id": "CAP-F1", "rel_type": "realizes"}

    def test_alt_field_names(self):
        raw = {"relationships": [{"from_id": "A", "to_id": "B", "rel_type": "depends-on"}]}
        out = normalize_llm_output("relate", raw)
        assert out["relationships"][0]["from_id"] == "A"
        assert out["relationships"][0]["rel_type"] == "depends-on"


class TestNormalizeSpecify:
    def test_basic(self):
        raw = {"interfaces": [{"name": "REST API", "type": "rest", "component_id": "COMP-1"}]}
        out = normalize_llm_output("specify", raw)
        assert out["interfaces"][0]["interface_type"] == "rest"

    def test_interface_type_field(self):
        raw = {"interfaces": [{"name": "X", "interface_type": "grpc", "component_id": "C"}]}
        out = normalize_llm_output("specify", raw)
        assert out["interfaces"][0]["interface_type"] == "grpc"


# ── apply_renames ────────────────────────────────────────────────────────


class TestApplyRenames:
    def _cap(self, id, name):
        return InferredCapability(id=id, name=name)

    def test_high_similarity_applied(self):
        entities = [self._cap("CAP-F1", "auth mgmt")]
        renames = [{"id": "CAP-F1", "det": "auth mgmt", "llm": "Authentication Management", "similarity": 0.75}]
        log = apply_renames(entities, renames, threshold=0.5)
        assert entities[0].name == "Authentication Management"
        assert len(log) == 1
        assert log[0]["old_name"] == "auth mgmt"

    def test_low_similarity_skipped(self):
        entities = [self._cap("CAP-F1", "X")]
        renames = [{"id": "CAP-F1", "det": "X", "llm": "Y", "similarity": 0.3}]
        log = apply_renames(entities, renames, threshold=0.5)
        assert entities[0].name == "X"
        assert log == []

    def test_threshold_edge_exact(self):
        entities = [self._cap("CAP-F1", "old")]
        renames = [{"id": "CAP-F1", "det": "old", "llm": "new", "similarity": 0.5}]
        log = apply_renames(entities, renames, threshold=0.5)
        assert entities[0].name == "new"
        assert len(log) == 1

    def test_no_matching_id(self):
        entities = [self._cap("CAP-F1", "old")]
        renames = [{"id": "CAP-F99", "det": "x", "llm": "y", "similarity": 0.9}]
        log = apply_renames(entities, renames)
        assert entities[0].name == "old"
        assert log == []


# ── apply_layer_corrections ──────────────────────────────────────────────


class TestApplyLayerCorrections:
    def test_applies_new_layer(self):
        comps = [ComponentAllocation(id="COMP-1", name="Web Controller", layer="services")]
        llm = [{"name": "Web Controller", "layer": "web"}]
        log = apply_layer_corrections(comps, llm)
        assert comps[0].layer == "web"
        assert len(log) == 1
        assert log[0]["old_layer"] == "services"
        assert log[0]["new_layer"] == "web"

    def test_no_change_same_layer(self):
        comps = [ComponentAllocation(id="COMP-1", name="API", layer="web")]
        llm = [{"name": "API", "layer": "web"}]
        log = apply_layer_corrections(comps, llm)
        assert log == []

    def test_low_similarity_no_match(self):
        comps = [ComponentAllocation(id="COMP-1", name="AAAA", layer="old")]
        llm = [{"name": "ZZZZ", "layer": "new"}]
        log = apply_layer_corrections(comps, llm)
        # similarity too low
        assert comps[0].layer == "old"


# ── apply_additions_infer ────────────────────────────────────────────────


class TestApplyAdditionsInfer:
    def test_add_capability(self):
        result = InferenceResult()
        added = [{"name": "New Cap"}]
        log = apply_additions_infer(result, added, id_counter=10)
        assert len(result.capabilities) == 1
        assert result.capabilities[0].id == "CAP-F10"
        assert result.capabilities[0].evidence_source == "llm"
        assert log[0]["entity_type"] == "capability"

    def test_add_behavior(self):
        result = InferenceResult()
        added = [{"name": "Login Flow", "type": "use_case"}]
        log = apply_additions_infer(result, added, id_counter=5)
        assert len(result.behaviors) == 1
        assert result.behaviors[0].id == "BEH-5"
        assert log[0]["entity_type"] == "behavior"

    def test_skip_empty_name(self):
        result = InferenceResult()
        log = apply_additions_infer(result, [{"name": ""}], id_counter=1)
        assert len(result.capabilities) == 0
        assert log == []

    def test_dedup_skips_similar(self):
        result = InferenceResult(
            capabilities=[InferredCapability(id="CAP-F1", name="MCP Server")],
        )
        added = [{"name": "Mcp Server Management"}]
        log = apply_additions_infer(result, added, id_counter=2)
        # Should not add — too similar
        assert len(result.capabilities) == 1
        # Log should contain a skipped_duplicates entry
        skipped_entries = [e for e in log if "skipped_duplicates" in e]
        assert len(skipped_entries) == 1
        assert skipped_entries[0]["skipped_duplicates"][0]["similar_to"] == "MCP Server"

    def test_dedup_allows_different(self):
        result = InferenceResult(
            capabilities=[InferredCapability(id="CAP-F1", name="MCP Server")],
        )
        added = [{"name": "Data Pipeline"}]
        log = apply_additions_infer(result, added, id_counter=2)
        assert len(result.capabilities) == 2
        assert result.capabilities[1].name == "Data Pipeline"
        assert any(e.get("entity_type") == "capability" for e in log)


# ── apply_additions_relate ───────────────────────────────────────────────


class TestApplyAdditionsRelate:
    def test_add_new(self):
        result = RelateResult()
        added = [{"from": "COMP-1", "to": "CAP-F1", "type": "realizes"}]
        log = apply_additions_relate(result, added)
        assert len(result.relationships) == 1
        assert result.relationships[0].from_id == "COMP-1"
        assert result.relationships[0].evidence_source == "llm"
        assert len(log) == 1

    def test_skip_duplicate(self):
        result = RelateResult(relationships=[
            DerivedRelationship(from_id="A", to_id="B", rel_type="depends-on"),
        ])
        added = [{"from": "A", "to": "B", "type": "realizes"}]
        log = apply_additions_relate(result, added)
        assert len(result.relationships) == 1  # not added
        assert log == []

    def test_skip_missing_ids(self):
        result = RelateResult()
        log = apply_additions_relate(result, [{"from": "", "to": "B", "type": "x"}])
        assert len(result.relationships) == 0
        assert log == []


# ── refine_with_llm ──────────────────────────────────────────────────────


def _make_stage_result(output):
    return StageResult(output=output, quality=QualityMetrics(score=0.8))


class _MockCtx:
    """Minimal mock for PipelineContext with llm_enrich."""

    def __init__(self, response=None, error=False):
        self._response = response
        self._error = error

    async def llm_enrich(self, stage, prompt, context=None):
        if self._error:
            return None
        return self._response


class TestRefineWithLlm:
    def test_non_refinable_stage_returns_original(self):
        ctx = _MockCtx()
        result = _make_stage_result("whatever")
        out, log = asyncio.run(refine_with_llm(ctx, "observe", {}, result))
        assert out is result
        assert log is None

    def test_llm_failure_returns_original(self):
        ctx = _MockCtx(error=True)
        infer_output = InferenceResult(
            capabilities=[InferredCapability(id="CAP-F1", name="old")],
        )
        result = _make_stage_result(infer_output)
        inputs = {"modules": [{"path": "x.py", "functions": [], "classes": []}]}
        out, log = asyncio.run(refine_with_llm(ctx, "infer", inputs, result))
        assert out is result
        assert log is None
        assert out.output.capabilities[0].name == "old"

    def test_json_parse_failure_returns_original(self):
        ctx = _MockCtx(response="not json at all {{{}}")
        infer_output = InferenceResult(
            capabilities=[InferredCapability(id="CAP-F1", name="old")],
        )
        result = _make_stage_result(infer_output)
        inputs = {"modules": [{"path": "x.py", "functions": [], "classes": []}]}
        out, log = asyncio.run(refine_with_llm(ctx, "infer", inputs, result))
        assert out is result
        assert log is None

    def test_infer_renames_capabilities(self):
        llm_response = json.dumps({
            "capabilities": [
                {"name": "Authentication Management", "source_file": "auth.py"},
            ],
            "behaviors": [],
        })
        ctx = _MockCtx(response=llm_response)
        infer_output = InferenceResult(
            capabilities=[InferredCapability(id="CAP-F1", name="auth", evidence_source="ast")],
        )
        result = _make_stage_result(infer_output)
        modules = [{"path": "auth.py", "functions": ["login"], "classes": []}]
        out, log = asyncio.run(refine_with_llm(ctx, "infer", {"modules": modules}, result))
        assert log is not None
        assert log.stage == "infer"
        assert log.duration_ms >= 0

    def test_allocate_corrects_layers(self):
        llm_response = json.dumps({
            "components": [
                {"name": "Web Controller", "files": ["web.py"], "layer": "web", "capability_id": "CAP-F1"},
            ],
        })
        ctx = _MockCtx(response=llm_response)
        alloc_output = AllocationResult(
            components=[ComponentAllocation(id="COMP-1", name="Web Controller", layer="infra")],
        )
        result = _make_stage_result(alloc_output)
        inputs = {"modules": [], "capabilities": []}
        out, log = asyncio.run(refine_with_llm(ctx, "allocate", inputs, result))
        assert log is not None
        assert log.stage == "allocate"
        # Layer should be corrected
        assert out.output.components[0].layer == "web"
        assert len(log.layer_corrections) == 1

    def test_relate_adds_relationships(self):
        llm_response = json.dumps({
            "relationships": [
                {"from": "COMP-1", "to": "CAP-F1", "type": "realizes"},
                {"from": "COMP-2", "to": "COMP-1", "type": "depends-on"},
            ],
        })
        ctx = _MockCtx(response=llm_response)
        relate_output = RelateResult(relationships=[
            DerivedRelationship(from_id="COMP-1", to_id="CAP-F1", rel_type="realizes"),
        ])
        result = _make_stage_result(relate_output)
        inputs = {"components": [], "capabilities": [], "imports": []}
        out, log = asyncio.run(refine_with_llm(ctx, "relate", inputs, result))
        assert log is not None
        assert log.stage == "relate"
        # The new relationship should be added
        assert len(out.output.relationships) == 2

    def test_specify_renames_interfaces(self):
        llm_response = json.dumps({
            "interfaces": [
                {"name": "REST API Gateway", "type": "rest", "component_id": "COMP-1"},
            ],
        })
        ctx = _MockCtx(response=llm_response)
        specify_output = SpecifyResult(interfaces=[
            InterfaceSpec(id="IF-1", name="REST API Gateway", component_id="COMP-1"),
        ])
        result = _make_stage_result(specify_output)
        inputs = {"components": []}
        out, log = asyncio.run(refine_with_llm(ctx, "specify", inputs, result))
        assert log is not None
        assert log.stage == "specify"

    def test_returns_refinement_log_with_timing(self):
        llm_response = json.dumps({
            "capabilities": [{"name": "Better Name", "source_file": "x.py"}],
            "behaviors": [],
        })
        ctx = _MockCtx(response=llm_response)
        infer_output = InferenceResult(
            capabilities=[InferredCapability(id="CAP-F1", name="old")],
        )
        result = _make_stage_result(infer_output)
        inputs = {"modules": [{"path": "x.py", "functions": [], "classes": []}]}
        out, log = asyncio.run(refine_with_llm(ctx, "infer", inputs, result))
        assert isinstance(log, RefinementLog)
        assert log.duration_ms >= 0


# ── RefinementLog summary & total_changes ────────────────────────────────


class TestRefinementLogSummary:
    def test_summary_mixed(self):
        log = RefinementLog(
            stage="infer",
            renames=[{"entity_id": "C1", "old_name": "a", "new_name": "b", "confidence": 0.8}],
            additions=[{"entity_type": "capability", "name": "X", "new_id": "CAP-F2"}],
            layer_corrections=[{"component_id": "C1", "old_layer": "x", "new_layer": "y"}],
        )
        s = log.summary()
        assert "1 renames" in s
        assert "1 additions" in s
        assert "1 layer corrections" in s

    def test_summary_relate(self):
        log = RefinementLog(
            stage="relate",
            additions=[{"from_id": "COMP-1", "to_id": "CAP-F1", "rel_type": "realizes"}],
        )
        s = log.summary()
        assert "COMP-1" in s
        assert "CAP-F1" in s
        assert "\u2192" in s

    def test_summary_empty(self):
        log = RefinementLog(stage="infer")
        assert log.summary() == "no changes"

    def test_total_changes(self):
        log = RefinementLog(
            stage="allocate",
            renames=[{"a": 1}, {"b": 2}],
            additions=[{"c": 3}],
            layer_corrections=[{"d": 4}, {"e": 5}, {"f": 6}],
        )
        assert log.total_changes == 6


# ── Mega-capability filtering ──────────────────────────────────────────


class TestMegaCapabilityReplacement:
    """When heuristic produces ≤3 caps and LLM produces ≥5, all LLM caps
    should be added directly (skipping diff/rename)."""

    def _make_result(self, cap_names: list[str]) -> StageResult:
        caps = [
            InferredCapability(id=f"CAP-F{i+1}", name=n)
            for i, n in enumerate(cap_names)
        ]
        infer = InferenceResult(capabilities=caps, actors=[], behaviors=[])
        return StageResult(
            output=infer,
            quality=QualityMetrics(score=80),
        )

    def test_mega_capability_replacement(self):
        """Heuristic has 1 cap, LLM has 6 → all 6 LLM caps added."""
        result = self._make_result(["Opencode Arch"])
        llm_caps = [
            {"name": n, "source_files": []}
            for n in ["Authentication", "Data Storage", "Logging", "Routing", "Validation", "Export"]
        ]
        llm_data = {"capabilities": llm_caps, "actors": [], "behaviors": []}

        # Import internals needed
        from architecture_model.pipeline.llm_refine import apply_additions_infer

        heuristic_cap_count = len(result.output.capabilities)
        llm_cap_count = len(llm_data.get("capabilities", []))
        assert heuristic_cap_count <= 3
        assert llm_cap_count >= 5

        all_llm_additions = llm_data["capabilities"] + llm_data["behaviors"]
        add_log = apply_additions_infer(
            result.output, all_llm_additions,
            id_counter=heuristic_cap_count + len(result.output.behaviors) + 1,
        )
        # All 6 should be added (none similar to "Opencode Arch")
        assert len(add_log) == 6
        # Total caps = 1 original + 6 added
        assert len(result.output.capabilities) == 7

    def test_normal_capability_no_replacement(self):
        """Heuristic has 5 caps, LLM has 7 → mega-cap path NOT triggered."""
        result = self._make_result([f"Cap {i}" for i in range(5)])
        llm_caps = [{"name": f"LLM Cap {i}", "source_files": []} for i in range(7)]
        llm_data = {"capabilities": llm_caps, "actors": [], "behaviors": []}

        heuristic_cap_count = len(result.output.capabilities)
        llm_cap_count = len(llm_data.get("capabilities", []))
        # Should NOT trigger mega-cap path
        assert not (heuristic_cap_count <= 3 and llm_cap_count >= 5)
