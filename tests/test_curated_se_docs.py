from __future__ import annotations

import re
from pathlib import Path

import pytest

from architecture_model.core.curated_views import build_curated_views
from architecture_model.core.parser import load_model
from architecture_model.docs.se.generator import generate_se_docs


LOGS_DB = Path("/Users/baigm2/Documents/Projects/logs_db")


def _section(markdown: str, heading: str) -> str:
    match = re.search(
        rf"^## {re.escape(heading)}\s*$\n(.*?)(?=^## |\Z)", markdown, re.MULTILINE | re.DOTALL,
    )
    assert match, f"missing section {heading}"
    return match.group(1)


@pytest.fixture
def curated_fixture(tmp_path: Path):
    (tmp_path / "evidence.md").write_text("fixture evidence", encoding="utf-8")
    (tmp_path / ".architecture-model.yaml").write_text(
        """meta: {project: Curated | Project, schema_version: '2.0'}
entities:
  actors:
    - {id: ACT-1, name: Canonical Actor, status: ACTIVE, goals: [Operate safely]}
  capabilities:
    - {id: CAP-1, name: Acquire, status: ACTIVE, requirements: [REQ-1], moes: [Records accepted]}
    - {id: CAP-2, name: Use, status: ACTIVE}
  components:
    - {id: COMP-1, name: Worker, status: ACTIVE, failure_modes: [Input rejected], monitored: [queue depth]}
  behaviors:
    - id: BEH-1
      name: Legacy behavior
      status: ACTIVE
      actor_id: ACT-1
      goals: [Canonical goal]
      trigger: Canonical trigger
      preconditions: [Ready]
      postconditions: [Completed]
      requirements: [REQ-1]
      structured_steps:
        - {order: 1, actor: Canonical Actor, action: Accept input, component_ref: COMP-1, input: request, output: result, error_handling: Reject invalid input}
  requirements:
    - {id: REQ-1, name: Reliable, status: ACTIVE}
relationships:
  - {from_id: COMP-1, to_id: CAP-1, type: realizes}
  - {from_id: COMP-1, to_id: BEH-1, type: traces-to}
""",
        encoding="utf-8",
    )
    curation = tmp_path / ".architecture" / "viewer-curation.yaml"
    curation.parent.mkdir()
    curation.write_text(
        """version: 1
views:
  conops:
    externals:
      - id: ext-source
        name: Source | System
        kind: source-system
        inferred: true
        evidence: [{source: evidence.md, claim: Source supplies records.}]
    scenarios:
      - id: scenario-acquire
        label: Acquire | Knowledge
        order: 1
        goal: Acquire records.
        outcomes: [Knowledge available]
        requirements: [Reliable]
        moes: [Records accepted]
        evidence: [{source: evidence.md, claim: Acquisition is supported.}]
        members: [root::BEH-1]
    flows:
      - source: ext-source
        target: scenario-acquire
        kind: exchange
        label: records | notes
        inferred: true
        evidence: [{source: evidence.md, claim: Records enter acquisition.}]
  functional:
    featured: [root::CAP-1, root::CAP-2]
    groups:
      - {id: function-acquire, label: Acquire | Function, order: 1, members: [root::CAP-1]}
      - {id: function-use, label: Use Function, order: 2, members: [root::CAP-2]}
    flows:
      - source: root::CAP-1
        target: root::CAP-2
        kind: data-flow
        label: records | context
        inferred: true
        evidence: [{source: evidence.md, claim: Acquired records are used.}]
  logical:
    tiers:
      - {id: tier-domain, label: Domain | Tier, order: 1, members: [root::COMP-1]}
    groups:
      - {id: aggregate-worker, label: Worker Aggregate, kind: aggregate, parent: tier-domain, members: [root::COMP-1]}
    aggregate_components: [root::COMP-1]
  use_cases:
    featured: [root::BEH-1]
    order: [root::BEH-1]
    labels: {root::BEH-1: Curated | Case}
    actors:
      - id: inferred-worker
        name: Inferred | Worker
        inferred: true
        evidence: [{source: evidence.md, claim: Worker initiates this case.}]
    associations:
      - actor: inferred-worker
        use_cases: [root::BEH-1]
        inferred: true
        evidence: [{source: evidence.md, claim: Worker uses the workflow.}]
""",
        encoding="utf-8",
    )
    model = load_model(tmp_path / ".architecture-model.yaml")
    return tmp_path, model


def test_curated_markdown_uses_the_same_spec_nodes_edges_and_safe_tables(curated_fixture) -> None:
    root, model = curated_fixture
    views = build_curated_views(model, root)
    output = root / "docs"
    result = generate_se_docs(
        model, output, repo_root=root,
        doc_filter=["conops", "functional_analysis", "logical_architecture", "use_cases"],
    )

    assert result["errors"] == []
    documents = {
        "conops": (output / "conops.md").read_text(),
        "functional": (output / "functional-analysis.md").read_text(),
        "logical": (output / "logical-architecture.md").read_text(),
        "use-cases": (output / "use-cases.md").read_text(),
    }
    for key, markdown in documents.items():
        for node in views[key]["spec"].nodes:
            assert node.label in markdown or node.label.replace("|", "\\|") in markdown
        for edge in views[key]["spec"].edges:
            assert edge.label.replace("|", "\\|") in markdown or edge.kind in markdown
        assert "Curation Status" in markdown
        assert views[key]["filename"] in markdown
    assert "Source \\| System" in documents["conops"]
    assert "records \\| notes" in documents["conops"]
    assert "Inferred" in documents["conops"] and "evidence.md" in documents["conops"]
    assert "Acquire \\| Function" in documents["functional"]
    assert "Inferred \\| Worker" in documents["use-cases"]


def test_direct_model_only_generators_preserve_legacy_narrative(curated_fixture) -> None:
    from architecture_model.docs.se.conops import generate_conops
    from architecture_model.docs.se.functional_analysis import generate_functional_analysis
    from architecture_model.docs.se.logical_architecture import generate_logical_architecture
    from architecture_model.docs.se.use_cases import generate_use_cases

    _, model = curated_fixture
    assert "Legacy behavior" in generate_conops(model)
    assert "Acquire" in generate_functional_analysis(model)
    assert "Worker" in generate_logical_architecture(model)
    assert "### UC: Legacy behavior" in generate_use_cases(model)


def test_label_only_curation_generates_conops_from_projected_scenarios(curated_fixture) -> None:
    root, model = curated_fixture
    (root / ".architecture" / "viewer-curation.yaml").write_text(
        """version: 1
views:
  conops:
    labels: {root::BEH-1: Curated operation}
""",
        encoding="utf-8",
    )

    result = generate_se_docs(model, root / "docs", repo_root=root, doc_filter=["conops"])

    assert result["errors"] == []
    assert "Curated operation" in (root / "docs" / "conops.md").read_text()


@pytest.mark.skipif(
    not (LOGS_DB / ".architecture/viewer-curation.yaml").is_file(),
    reason="optional logs-db fixture is unavailable",
)
def test_actual_logs_db_curated_primary_sections_match_executive_views(tmp_path: Path) -> None:
    model = load_model(LOGS_DB / ".architecture-model.yaml")
    result = generate_se_docs(
        model, tmp_path, repo_root=LOGS_DB,
        doc_filter=["conops", "functional_analysis", "logical_architecture", "use_cases"],
    )
    assert result["errors"] == []

    conops = (tmp_path / "conops.md").read_text()
    scenario_section = _section(conops, "Operational Scenarios")
    expected_scenarios = ["Acquire Knowledge", "Enrich & Organize", "Search & Use", "Review & Govern", "Learn & Improve"]
    assert [scenario_section.index(f"### {name}") for name in expected_scenarios] == sorted(
        scenario_section.index(f"### {name}") for name in expected_scenarios
    )
    assert "GitHub / OpenCode" in _section(conops, "Stakeholders")
    assert "API Consumer" in _section(conops, "Stakeholders")
    assert "Acquire Multi-Source Knowledge" not in scenario_section

    functional = (tmp_path / "functional-analysis.md").read_text()
    inventory = _section(functional, "Capability Inventory and Decomposition")
    expected_functions = [
        "Ingestion", "Classification & Enrichment", "Curation & Audit", "Search & Graph",
        "Review & Lifecycle", "Project Context", "Documentation Automation",
        "Training & Evaluation", "Architecture & Drift", "Persistence & Schema",
    ]
    assert all(f"### {name}" in inventory for name in expected_functions)
    assert len(re.findall(r"^\| .* \| .* \| .* \| .* \| .* \|$", _section(functional, "Functional Flows"), re.MULTILINE)) - 1 == 7
    assert "365" in _section(functional, "Appendix: Overview Omissions")

    logical = (tmp_path / "logical-architecture.md").read_text()
    tier_section = _section(logical, "Logical Tiers and Systems")
    assert all(name in tier_section for name in ["Web", "Application / Orchestration", "Domain / Service", "Data / Contracts", "Infrastructure"])
    assert "No layers defined" not in logical
    assert "full dependencies live in system drilldowns" in logical

    use_cases = (tmp_path / "use-cases.md").read_text()
    matrix = _section(use_cases, "Actor-Goal Matrix")
    assert "Knowledge Worker" in matrix and "Automation Operator" in matrix and "API Consumer" in matrix
    catalog = _section(use_cases, "Featured Use Case Catalog")
    expected_cases = [
        "Ingest Multi-Source Knowledge", "Ingest Conversation History", "Ingest Coursework",
        "Ingest Goals & Career Evidence", "Collect Project Documentation Context",
        "Curate Knowledge Base Entities", "Manage Log Capture, Review & Lifecycle",
        "Manage Project Portfolio Context", "Manage Artifact Feedback Constraints",
        "Validate Generated Artifacts",
    ]
    assert re.findall(r"^### UC: (.+)$", catalog, re.MULTILINE) == expected_cases
    assert "279" in _section(use_cases, "Appendix: Overview Omissions")
    assert "Inferred" in catalog and "scripts/_pipeline_ingest.py" in catalog
