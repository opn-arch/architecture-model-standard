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
