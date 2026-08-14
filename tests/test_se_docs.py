"""Tests for SE document generation system."""
from __future__ import annotations
import pytest
from pathlib import Path
import hashlib


class TestChangelog:
    """Tests for changelog tracking."""

    def test_new_changelog_created(self, tmp_path: Path) -> None:
        from architecture_model.docs.se.changelog import Changelog
        cl = Changelog(tmp_path / "changelog.yaml")
        cl.record_generation("conops.md", author="architect_pipeline", model_hash="abc123")
        data = cl.load()
        assert "conops.md" in data["documents"]
        entry = data["documents"]["conops.md"]
        assert entry["created_by"] == "architect_pipeline"
        assert len(entry["editions"]) == 1
        assert entry["editions"][0]["type"] == "generated"

    def test_detect_user_edit(self, tmp_path: Path) -> None:
        from architecture_model.docs.se.changelog import Changelog
        cl = Changelog(tmp_path / "changelog.yaml")
        # Record initial generation with section hashes
        cl.record_generation("conops.md", author="architect_pipeline", model_hash="abc123",
                             section_hashes={"Overview": "hash1", "Actors": "hash2"})
        # Simulate user editing by providing different hashes on check
        edits = cl.detect_edits("conops.md",
                                current_hashes={"Overview": "hash1", "Actors": "CHANGED"})
        assert edits == ["Actors"]

    def test_record_regeneration_preserves_user_edits(self, tmp_path: Path) -> None:
        from architecture_model.docs.se.changelog import Changelog
        cl = Changelog(tmp_path / "changelog.yaml")
        cl.record_generation("conops.md", author="architect_pipeline", model_hash="abc123",
                             section_hashes={"Overview": "h1"})
        cl.record_regeneration("conops.md", author="architect_pipeline", model_hash="def456",
                               preserved_sections=["Overview"], summary="Model updated")
        data = cl.load()
        editions = data["documents"]["conops.md"]["editions"]
        assert len(editions) == 2
        assert editions[1]["type"] == "regenerated"
        assert "Overview" in editions[1]["preserved_sections"]


class TestFrontmatter:
    """Tests for document frontmatter."""

    def test_generate_frontmatter(self) -> None:
        from architecture_model.docs.se.frontmatter import generate_frontmatter
        fm = generate_frontmatter(document="ConOps", system="Django", system_id="SYS-1",
                                  model_hash="abc123", edition=1)
        assert "---" in fm
        assert "document: ConOps" in fm
        assert "system: Django" in fm
        assert "edition: 1" in fm

    def test_parse_frontmatter(self) -> None:
        from architecture_model.docs.se.frontmatter import parse_frontmatter
        doc = "---\ndocument: ConOps\nedition: 2\n---\n# ConOps\nContent here"
        meta, body = parse_frontmatter(doc)
        assert meta["document"] == "ConOps"
        assert meta["edition"] == 2
        assert body.startswith("# ConOps")

    def test_extract_section_hashes(self) -> None:
        from architecture_model.docs.se.frontmatter import extract_section_hashes
        doc = "# Doc\n## Overview\nSome text\n## Actors\nMore text\n## Scenarios\nFinal"
        hashes = extract_section_hashes(doc)
        assert "Overview" in hashes
        assert "Actors" in hashes
        assert "Scenarios" in hashes
        # Each hash is a hex string
        assert all(len(h) == 32 for h in hashes.values())  # md5 hex length


def _make_model():
    """Build a minimal ArchitectureModel with all 7 entity types for testing."""
    from architecture_model.core.parser import _parse_raw
    raw = {
        "meta": {"schema_version": "2.0", "project": "TestProject"},
        "entities": {
            "actors": [{"id": "ACT-1", "name": "Developer", "type": "human", "goals": ["Build features"]}],
            "capabilities": [
                {"id": "CAP-1", "name": "Data Processing", "status": "ACTIVE"},
                {"id": "CAP-2", "name": "User Management", "status": "ACTIVE"},
            ],
            "behaviors": [
                {"id": "BEH-1", "name": "Submit Form", "trigger": "user action",
                 "actor": "ACT-1", "steps": ["Validate input", "Save data", "Return response"],
                 "preconditions": ["User authenticated"], "postconditions": ["Data saved"]},
                {"id": "BEH-2", "name": "Middleware Pipeline", "trigger": "HTTP request",
                 "steps": ["Process request", "Call view", "Process response"]},
            ],
            "interfaces": [
                {"id": "INT-1", "name": "REST API", "type": "REST", "provider": "COMP-1",
                 "consumer": "ACT-1", "endpoints": [{"path": "/api/data", "method": "GET"}]},
            ],
            "constraints": [
                {"id": "CON-1", "name": "Python 3.10+", "type": "technology", "rationale": "Type hints"},
                {"id": "CON-2", "name": "Response < 200ms", "type": "performance",
                 "metric": "latency", "threshold": "200ms"},
            ],
            "layers": [
                {"id": "LYR-1", "name": "web", "order": 1},
                {"id": "LYR-2", "name": "data", "order": 2},
            ],
            "components": [
                {"id": "COMP-1", "name": "APIServer", "layer": "web",
                 "files": ["src/api.py"], "kind": "service",
                 "responsibilities": ["Handle HTTP requests"]},
                {"id": "COMP-2", "name": "DataStore", "layer": "data",
                 "files": ["src/db.py"], "kind": "data-store",
                 "responsibilities": ["Persist data"]},
            ],
        },
        "relationships": [
            {"from": "COMP-1", "to": "CAP-1", "type": "realizes"},
            {"from": "COMP-1", "to": "COMP-2", "type": "depends-on"},
            {"from": "COMP-1", "to": "CON-2", "type": "constrained-by"},
            {"from": "BEH-1", "to": "BEH-2", "type": "triggers"},
            {"from": "ACT-1", "to": "INT-1", "type": "consumes"},
        ],
    }
    return _parse_raw(raw)


class TestConOps:
    def test_generates_conops(self) -> None:
        from architecture_model.docs.se.conops import generate_conops
        model = _make_model()
        md = generate_conops(model)
        assert "# Concept of Operations" in md
        assert "Developer" in md  # actor name
        assert "Submit Form" in md  # use case behavior
        assert "REST API" in md  # interface

    def test_conops_has_required_sections(self) -> None:
        from architecture_model.docs.se.conops import generate_conops
        model = _make_model()
        md = generate_conops(model)
        for section in ["System Overview", "Stakeholders", "Operational Scenarios",
                        "System Context", "Operational Constraints"]:
            assert f"## {section}" in md, f"Missing section: {section}"


class TestOrchestrator:
    def test_generate_se_docs_creates_files(self, tmp_path: Path) -> None:
        from architecture_model.docs.se.generator import generate_se_docs
        model = _make_model()
        result = generate_se_docs(model, tmp_path)
        assert (tmp_path / "conops.md").exists()
        assert (tmp_path / "changelog.yaml").exists()
        assert len(result["generated"]) >= 1

    def test_regeneration_preserves_user_edits(self, tmp_path: Path) -> None:
        from architecture_model.docs.se.generator import generate_se_docs
        model = _make_model()
        # First generation
        generate_se_docs(model, tmp_path)
        # Simulate user edit
        conops = tmp_path / "conops.md"
        original = conops.read_text()
        conops.write_text(original.replace("## System Overview", "## System Overview\nUser added this line."))
        # Regenerate — user-edited section should be preserved
        result = generate_se_docs(model, tmp_path)
        new_content = conops.read_text()
        assert "User added this line." in new_content


class TestFunctionalAnalysis:
    def test_generates_functional_analysis(self) -> None:
        from architecture_model.docs.se.functional_analysis import generate_functional_analysis
        model = _make_model()
        md = generate_functional_analysis(model)
        assert "# Functional Analysis" in md
        assert "Data Processing" in md  # capability
        assert "COMP-1" in md or "APIServer" in md  # component realizing capability

    def test_has_required_sections(self) -> None:
        from architecture_model.docs.se.functional_analysis import generate_functional_analysis
        model = _make_model()
        md = generate_functional_analysis(model)
        for section in ["Capability Inventory", "Functional Decomposition",
                        "Capability-Component Mapping"]:
            assert f"## {section}" in md, f"Missing: {section}"


class TestLogicalArchitecture:
    def test_generates_logical_architecture(self) -> None:
        from architecture_model.docs.se.logical_architecture import generate_logical_architecture
        model = _make_model()
        md = generate_logical_architecture(model)
        assert "# Logical Architecture" in md
        assert "web" in md  # layer
        assert "APIServer" in md  # component

    def test_has_mermaid_diagram(self) -> None:
        from architecture_model.docs.se.logical_architecture import generate_logical_architecture
        model = _make_model()
        md = generate_logical_architecture(model)
        assert "```mermaid" in md

    def test_has_required_sections(self) -> None:
        from architecture_model.docs.se.logical_architecture import generate_logical_architecture
        model = _make_model()
        md = generate_logical_architecture(model)
        for section in ["Layer Structure", "Component Allocation", "Inter-Component Interfaces",
                        "Dependency Graph"]:
            assert f"## {section}" in md, f"Missing: {section}"


class TestRequirementsAnalysis:
    def test_generates_requirements_analysis(self) -> None:
        from architecture_model.docs.se.requirements_analysis import generate_requirements_analysis
        model = _make_model()
        md = generate_requirements_analysis(model)
        assert "# Requirements Analysis" in md
        assert "Python 3.10+" in md  # constraint
        assert "constrained-by" in md or "Traceability" in md

    def test_has_required_sections(self) -> None:
        from architecture_model.docs.se.requirements_analysis import generate_requirements_analysis
        model = _make_model()
        md = generate_requirements_analysis(model)
        for section in ["Constraint Inventory", "Requirements Traceability",
                        "Constraint Allocation", "Coverage Gaps"]:
            assert f"## {section}" in md, f"Missing: {section}"


class TestVerificationValidation:
    def test_generates_vv(self) -> None:
        from architecture_model.docs.se.verification_validation import generate_verification_validation
        model = _make_model()
        md = generate_verification_validation(model)
        assert "# Verification & Validation" in md

    def test_has_required_sections(self) -> None:
        from architecture_model.docs.se.verification_validation import generate_verification_validation
        model = _make_model()
        md = generate_verification_validation(model)
        for section in ["Verification Matrix", "Validation Coverage", "Unverified Items"]:
            assert f"## {section}" in md, f"Missing: {section}"


class TestOperationsManual:
    def test_generates_operations_manual(self) -> None:
        from architecture_model.docs.se.operations_manual import generate_operations_manual
        model = _make_model()
        md = generate_operations_manual(model)
        assert "# Operations Manual" in md
        assert "REST API" in md

    def test_has_required_sections(self) -> None:
        from architecture_model.docs.se.operations_manual import generate_operations_manual
        model = _make_model()
        md = generate_operations_manual(model)
        for section in ["Interface Catalog", "Operational Workflows",
                        "Configuration & Constraints", "Error Handling"]:
            assert f"## {section}" in md, f"Missing: {section}"


class TestMaintenanceManual:
    def test_generates_maintenance_manual(self) -> None:
        from architecture_model.docs.se.maintenance_manual import generate_maintenance_manual
        model = _make_model()
        md = generate_maintenance_manual(model)
        assert "# Maintenance Manual" in md
        assert "APIServer" in md

    def test_has_required_sections(self) -> None:
        from architecture_model.docs.se.maintenance_manual import generate_maintenance_manual
        model = _make_model()
        md = generate_maintenance_manual(model)
        for section in ["Component Inventory", "Dependency Impact Analysis",
                        "Modification Procedures", "Known Constraints"]:
            assert f"## {section}" in md, f"Missing: {section}"


class TestUseCases:
    def test_generates_use_cases(self) -> None:
        from architecture_model.docs.se.use_cases import generate_use_cases
        model = _make_model()
        md = generate_use_cases(model)
        assert "# Use Cases" in md
        assert "Submit Form" in md
        assert "Developer" in md

    def test_has_required_sections(self) -> None:
        from architecture_model.docs.se.use_cases import generate_use_cases
        model = _make_model()
        md = generate_use_cases(model)
        for section in ["Actor-Goal Matrix", "Use Case Specifications", "Use Case Diagram"]:
            assert f"## {section}" in md, f"Missing: {section}"


class TestRiskAssessment:
    def test_generates_risk_assessment(self) -> None:
        from architecture_model.docs.se.risk_assessment import generate_risk_assessment
        model = _make_model()
        md = generate_risk_assessment(model)
        assert "# Risk Assessment" in md

    def test_has_required_sections(self) -> None:
        from architecture_model.docs.se.risk_assessment import generate_risk_assessment
        model = _make_model()
        md = generate_risk_assessment(model)
        for section in ["Risk Register", "Dependency Risks", "Constraint Risks"]:
            assert f"## {section}" in md, f"Missing: {section}"


class TestInterfaceSpec:
    def test_generates_interface_spec(self) -> None:
        from architecture_model.docs.se.interface_spec import generate_interface_spec
        model = _make_model()
        md = generate_interface_spec(model)
        assert "# Interface Specification" in md
        assert "REST API" in md

    def test_has_required_sections(self) -> None:
        from architecture_model.docs.se.interface_spec import generate_interface_spec
        model = _make_model()
        md = generate_interface_spec(model)
        for section in ["Interface Inventory", "Interface Details"]:
            assert f"## {section}" in md, f"Missing: {section}"
