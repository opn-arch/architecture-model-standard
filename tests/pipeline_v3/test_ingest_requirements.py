"""Tests for R8: Requirements ingestion from documentation.

Covers the ``ingest_requirements`` stage that scans authored docs
and attaches doc-sourced requirements to model entities as promises.

Design: ``docs/plans/2026-09-20-r8-requirements-ingestion-design.md``.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from architecture_model.core.promise import Promise, PromiseStatus
from architecture_model.pipeline_v3.ingest_requirements import (
    DEFAULT_DOC_ROOTS,
    DocSection,
    _classify_llm,
    _extract_requirements,
    _parse_frontmatter,
    _parse_sections,
    _try_exact_heading_match,
    _try_explicit_marker,
    ingest_requirements,
    scan_docs,
)


# --------------------------------------------------------------------------
# Provider fixture
# --------------------------------------------------------------------------


class MockProvider:
    """Provider scripting for Layer 3 tests."""

    name = "mock"

    def __init__(self, script):
        # script: callable(prompt, schema) -> dict OR a fixed dict.
        self._script = script
        self.calls: list[tuple[str, dict]] = []

    def structured(self, prompt: str, schema: dict, *, model=None) -> dict:
        self.calls.append((prompt, schema))
        if callable(self._script):
            return self._script(prompt, schema)
        return dict(self._script)

    def complete(self, *a, **kw):  # pragma: no cover
        raise NotImplementedError

    def stream(self, *a, **kw):  # pragma: no cover
        raise NotImplementedError

    def tokenize(self, text):  # pragma: no cover
        return len(text.split())


# --------------------------------------------------------------------------
# Model fixture
# --------------------------------------------------------------------------


def _mk_promise(owner, attribute, content, status=PromiseStatus.OPEN):
    return Promise(
        attribute=attribute,
        content=content,
        owner_entity=owner,
        status=status,
    ).to_dict()


@pytest.fixture
def tiny_model():
    return {
        "meta": {"schema_version": "3.0"},
        "entities": {
            "components": [
                {"id": "COMP-A", "name": "AuthService", "promises": []},
                {"id": "COMP-B", "name": "PaymentGateway", "promises": []},
            ],
            "capabilities": [
                {"id": "CAP-A", "name": "Authenticate Users", "promises": []},
            ],
            "behaviors": [
                {"id": "BEH-A", "name": "login_flow", "promises": []},
            ],
            "actors": [{"id": "ACT-A", "name": "EndUser", "promises": []}],
        },
        "relationships": [],
    }


# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------


def test_default_doc_roots_contains_expected_paths():
    assert set(DEFAULT_DOC_ROOTS) == {
        "docs/reports",
        "docs/plans",
        "CONTEXT.md",
        "README.md",
    }


# --------------------------------------------------------------------------
# Frontmatter parsing
# --------------------------------------------------------------------------


def test_parse_frontmatter_returns_dict_and_body():
    text = "---\nbinds_to: COMP-A\ntitle: X\n---\n\n# Heading\n\nbody\n"
    fm, body = _parse_frontmatter(text)
    assert fm == {"binds_to": "COMP-A", "title": "X"}
    assert body.startswith("# Heading")


def test_parse_frontmatter_no_frontmatter_returns_empty_dict():
    text = "# Heading\n\nbody\n"
    fm, body = _parse_frontmatter(text)
    assert fm == {}
    assert body == text


def test_parse_frontmatter_malformed_yaml_returns_empty_dict():
    text = "---\n: : not: valid: yaml:\n---\n\n# H\nbody\n"
    fm, body = _parse_frontmatter(text)
    # Malformed frontmatter must not raise.
    assert fm == {}
    # Body should still be produced (may include the raw block or skip it).
    assert "# H" in body


# --------------------------------------------------------------------------
# Section splitting
# --------------------------------------------------------------------------


def test_parse_sections_splits_by_atx_headings():
    text = (
        "# Top\n\nintro\n\n"
        "## AuthService\n\nsection body\n"
        "- req one\n"
        "\n"
        "## PaymentGateway\n\nanother body\n"
    )
    sections = _parse_sections(text, frontmatter={}, path="docs/x.md")
    headings = [(s.heading, s.heading_level) for s in sections]
    assert ("Top", 1) in headings
    assert ("AuthService", 2) in headings
    assert ("PaymentGateway", 2) in headings


def test_parse_sections_captures_inline_binds_marker():
    text = "## Foo <!-- binds: COMP-A -->\n\nbody\n"
    sections = _parse_sections(text, frontmatter={}, path="docs/x.md")
    assert len(sections) == 1
    assert sections[0].inline_binds_to == "COMP-A"


def test_parse_sections_captures_anchor_id():
    text = "## Foo {#COMP-B}\n\nbody\n"
    sections = _parse_sections(text, frontmatter={}, path="docs/x.md")
    assert len(sections) == 1
    assert sections[0].anchor_id == "COMP-B"


def test_parse_sections_frontmatter_bound_to_every_section():
    fm = {"binds_to": "COMP-A"}
    text = "## Sec\n\nbody\n"
    sections = _parse_sections(text, frontmatter=fm, path="docs/x.md")
    assert sections[0].frontmatter == fm


# --------------------------------------------------------------------------
# scan_docs
# --------------------------------------------------------------------------


def test_scan_docs_walks_configured_roots(tmp_path: Path):
    (tmp_path / "docs" / "reports").mkdir(parents=True)
    (tmp_path / "docs" / "reports" / "r1.md").write_text(
        "## A\n\nbody\n\n## B\n\nbody2\n"
    )
    (tmp_path / "CONTEXT.md").write_text("## C\n\nbody\n")

    sections = scan_docs(tmp_path, doc_roots=("docs/reports", "CONTEXT.md"))
    headings = [s.heading for s in sections]
    assert set(headings) == {"A", "B", "C"}


def test_scan_docs_deterministic_order(tmp_path: Path):
    (tmp_path / "docs" / "plans").mkdir(parents=True)
    (tmp_path / "docs" / "plans" / "z.md").write_text("## Z\nbody\n")
    (tmp_path / "docs" / "plans" / "a.md").write_text("## A\nbody\n")
    (tmp_path / "docs" / "plans" / "m.md").write_text("## M\nbody\n")
    sections = scan_docs(tmp_path, doc_roots=("docs/plans",))
    order = [s.heading for s in sections]
    assert order == ["A", "M", "Z"]


def test_scan_docs_missing_root_silently_skipped(tmp_path: Path):
    # No files created — every root missing.
    sections = scan_docs(tmp_path, doc_roots=("docs/reports", "MISSING.md"))
    assert sections == []


def test_scan_docs_skips_non_markdown(tmp_path: Path):
    (tmp_path / "docs" / "reports").mkdir(parents=True)
    (tmp_path / "docs" / "reports" / "keep.md").write_text("## K\nbody\n")
    (tmp_path / "docs" / "reports" / "skip.txt").write_text("not markdown\n")
    (tmp_path / "docs" / "reports" / "skip.png").write_bytes(b"\x89PNG")
    sections = scan_docs(tmp_path, doc_roots=("docs/reports",))
    assert [s.heading for s in sections] == ["K"]


# --------------------------------------------------------------------------
# Requirement extraction
# --------------------------------------------------------------------------


def test_extract_requirements_from_bullet_list():
    body = "Some intro prose.\n\n- first requirement\n- second requirement\n"
    items = _extract_requirements(body)
    assert items == ["first requirement", "second requirement"]


def test_extract_requirements_from_numbered_list():
    body = "1. one\n2. two\n3. three\n"
    items = _extract_requirements(body)
    assert items == ["one", "two", "three"]


def test_extract_requirements_flattens_nested_lists():
    body = "- top\n  - nested\n- second top\n"
    items = _extract_requirements(body)
    assert "top" in items
    assert "nested" in items
    assert "second top" in items


def test_extract_requirements_empty_body_returns_empty():
    assert _extract_requirements("") == []
    assert _extract_requirements("just prose no bullets") == []


# --------------------------------------------------------------------------
# Binding — Layer 1 (explicit markers)
# --------------------------------------------------------------------------


def test_layer1_frontmatter_binds_to_wins(tiny_model):
    section = DocSection(
        path="docs/x.md",
        heading="Some Heading",
        heading_level=2,
        body="- req\n",
        frontmatter={"binds_to": "COMP-A"},
        inline_binds_to=None,
        anchor_id=None,
    )
    result = _try_explicit_marker(section, tiny_model)
    assert result == "COMP-A"


def test_layer1_inline_comment_wins(tiny_model):
    section = DocSection(
        path="docs/x.md",
        heading="Random",
        heading_level=2,
        body="- x\n",
        frontmatter={},
        inline_binds_to="COMP-B",
        anchor_id=None,
    )
    assert _try_explicit_marker(section, tiny_model) == "COMP-B"


def test_layer1_anchor_id_wins(tiny_model):
    section = DocSection(
        path="docs/x.md",
        heading="Random",
        heading_level=2,
        body="- x\n",
        frontmatter={},
        inline_binds_to=None,
        anchor_id="CAP-A",
    )
    assert _try_explicit_marker(section, tiny_model) == "CAP-A"


def test_layer1_unknown_entity_id_returns_none(tiny_model):
    section = DocSection(
        path="docs/x.md",
        heading="X",
        heading_level=2,
        body="",
        frontmatter={"binds_to": "COMP-DOES-NOT-EXIST"},
        inline_binds_to=None,
        anchor_id=None,
    )
    assert _try_explicit_marker(section, tiny_model) is None


# --------------------------------------------------------------------------
# Binding — Layer 2 (exact heading match)
# --------------------------------------------------------------------------


def test_layer2_exact_name_match(tiny_model):
    section = DocSection(
        path="docs/x.md",
        heading="AuthService",
        heading_level=2,
        body="- req\n",
        frontmatter={},
        inline_binds_to=None,
        anchor_id=None,
    )
    assert _try_exact_heading_match(section, tiny_model) == "COMP-A"


def test_layer2_case_insensitive(tiny_model):
    section = DocSection(
        path="docs/x.md",
        heading="AUTHSERVICE",
        heading_level=2,
        body="",
        frontmatter={},
        inline_binds_to=None,
        anchor_id=None,
    )
    assert _try_exact_heading_match(section, tiny_model) == "COMP-A"


def test_layer2_punctuation_normalized(tiny_model):
    section = DocSection(
        path="docs/x.md",
        heading="Authenticate Users!",
        heading_level=2,
        body="",
        frontmatter={},
        inline_binds_to=None,
        anchor_id=None,
    )
    assert _try_exact_heading_match(section, tiny_model) == "CAP-A"


def test_layer2_no_match_returns_none(tiny_model):
    section = DocSection(
        path="docs/x.md",
        heading="Unrelated Heading",
        heading_level=2,
        body="",
        frontmatter={},
        inline_binds_to=None,
        anchor_id=None,
    )
    assert _try_exact_heading_match(section, tiny_model) is None


# --------------------------------------------------------------------------
# Binding — Layer 3 (LLM classifier)
# --------------------------------------------------------------------------


def test_layer3_provider_high_confidence_returns_id(tiny_model):
    section = DocSection(
        path="docs/x.md",
        heading="Payment Gateway Integration",  # fuzzy vs "PaymentGateway"
        heading_level=2,
        body="body about payments",
        frontmatter={},
        inline_binds_to=None,
        anchor_id=None,
    )
    provider = MockProvider({"entity_id": "COMP-B", "confidence": 0.9})
    result = _classify_llm(section, tiny_model, provider, threshold=0.75)
    assert result == "COMP-B"


def test_layer3_provider_low_confidence_returns_none(tiny_model):
    section = DocSection(
        path="docs/x.md",
        heading="Payment Gateway Integration",
        heading_level=2,
        body="",
        frontmatter={},
        inline_binds_to=None,
        anchor_id=None,
    )
    provider = MockProvider({"entity_id": "COMP-B", "confidence": 0.4})
    result = _classify_llm(section, tiny_model, provider, threshold=0.75)
    assert result is None


def test_layer3_provider_null_entity_returns_none(tiny_model):
    section = DocSection(
        path="docs/x.md",
        heading="Payment Gateway Integration",
        heading_level=2,
        body="",
        frontmatter={},
        inline_binds_to=None,
        anchor_id=None,
    )
    provider = MockProvider({"entity_id": None, "confidence": 0.9})
    assert _classify_llm(section, tiny_model, provider, threshold=0.75) is None


def test_layer3_provider_missing_returns_none(tiny_model):
    section = DocSection(
        path="docs/x.md",
        heading="Payment Gateway",
        heading_level=2,
        body="",
        frontmatter={},
        inline_binds_to=None,
        anchor_id=None,
    )
    # provider=None
    assert _classify_llm(section, tiny_model, None) is None


def test_layer3_provider_exception_returns_none(tiny_model):
    section = DocSection(
        path="docs/x.md",
        heading="X",
        heading_level=2,
        body="",
        frontmatter={},
        inline_binds_to=None,
        anchor_id=None,
    )

    def blow_up(prompt, schema):
        raise RuntimeError("provider down")

    provider = MockProvider(blow_up)
    assert _classify_llm(section, tiny_model, provider) is None


def test_layer3_only_runs_when_heading_shares_token(tiny_model):
    """Optimization: no LLM call if heading shares no token with any entity name."""
    section = DocSection(
        path="docs/x.md",
        heading="XYZ ABC 123",  # No overlap with entity names.
        heading_level=2,
        body="",
        frontmatter={},
        inline_binds_to=None,
        anchor_id=None,
    )
    provider = MockProvider({"entity_id": "COMP-A", "confidence": 1.0})
    result = _classify_llm(section, tiny_model, provider)
    assert result is None
    assert provider.calls == []


# --------------------------------------------------------------------------
# End-to-end
# --------------------------------------------------------------------------


def test_ingest_requirements_end_to_end_layer1(tmp_path: Path, tiny_model):
    (tmp_path / "docs" / "reports").mkdir(parents=True)
    (tmp_path / "docs" / "reports" / "auth.md").write_text(
        "---\nbinds_to: COMP-A\n---\n\n"
        "## Some Heading\n\n"
        "- req A\n- req B\n"
    )
    result = ingest_requirements(
        tiny_model,
        repo_path=tmp_path,
        doc_roots=("docs/reports",),
    )
    comp = next(c for c in result["entities"]["components"] if c["id"] == "COMP-A")
    reqs = [p for p in comp["promises"] if p["attribute"] == "requirements"]
    assert len(reqs) == 2
    # Layer 1 → verified.
    assert all(p["status"] == PromiseStatus.VERIFIED.value for p in reqs)
    # verified_by carries the doc path.
    for p in reqs:
        assert any("auth.md" in v for v in p["verified_by"])


def test_ingest_requirements_end_to_end_layer2(tmp_path: Path, tiny_model):
    (tmp_path / "docs" / "reports").mkdir(parents=True)
    (tmp_path / "docs" / "reports" / "authservice.md").write_text(
        "## AuthService\n\n- must verify JWT signature\n- must expire tokens\n"
    )
    result = ingest_requirements(
        tiny_model,
        repo_path=tmp_path,
        doc_roots=("docs/reports",),
    )
    comp = next(c for c in result["entities"]["components"] if c["id"] == "COMP-A")
    reqs = [p for p in comp["promises"] if p["attribute"] == "requirements"]
    assert len(reqs) == 2
    assert all(p["status"] == PromiseStatus.VERIFIED.value for p in reqs)


def test_ingest_requirements_end_to_end_layer3_with_provider(tmp_path: Path, tiny_model):
    (tmp_path / "docs" / "reports").mkdir(parents=True)
    (tmp_path / "docs" / "reports" / "pay.md").write_text(
        "## Payment Gateway Integration\n\n- must charge cards\n"
    )
    provider = MockProvider({"entity_id": "COMP-B", "confidence": 0.9})
    result = ingest_requirements(
        tiny_model,
        repo_path=tmp_path,
        doc_roots=("docs/reports",),
        provider=provider,
    )
    comp = next(c for c in result["entities"]["components"] if c["id"] == "COMP-B")
    reqs = [p for p in comp["promises"] if p["attribute"] == "requirements"]
    assert len(reqs) == 1
    # Layer 3 → proposed (LLM-classified).
    assert reqs[0]["status"] == PromiseStatus.PROPOSED.value


def test_ingest_requirements_deletes_r7_proposed_requirements(tmp_path: Path, tiny_model):
    """R7's proposed requirements are wiped before R8 attaches doc-grounded ones."""
    # Simulate R7 output already on the component.
    r7_proposed = _mk_promise(
        "COMP-A", "requirements", "R7 guessed this", status=PromiseStatus.PROPOSED
    )
    tiny_model["entities"]["components"][0]["promises"].append(r7_proposed)

    (tmp_path / "docs" / "reports").mkdir(parents=True)
    (tmp_path / "docs" / "reports" / "auth.md").write_text(
        "## AuthService\n\n- doc-grounded req\n"
    )
    result = ingest_requirements(
        tiny_model,
        repo_path=tmp_path,
        doc_roots=("docs/reports",),
    )
    comp = next(c for c in result["entities"]["components"] if c["id"] == "COMP-A")
    reqs = [p for p in comp["promises"] if p["attribute"] == "requirements"]
    # R7 guess deleted; doc-grounded req added.
    assert len(reqs) == 1
    assert reqs[0]["content"] == "doc-grounded req"
    assert reqs[0]["status"] == PromiseStatus.VERIFIED.value


def test_ingest_requirements_preserves_verified_promises(tmp_path: Path, tiny_model):
    """Existing verified promises for `requirements` are NEVER touched."""
    verified = _mk_promise(
        "COMP-A", "requirements", "human authored", status=PromiseStatus.VERIFIED
    )
    tiny_model["entities"]["components"][0]["promises"].append(verified)

    (tmp_path / "docs" / "reports").mkdir(parents=True)
    (tmp_path / "docs" / "reports" / "x.md").write_text(
        "## AuthService\n\n- doc req\n"
    )
    result = ingest_requirements(
        tiny_model,
        repo_path=tmp_path,
        doc_roots=("docs/reports",),
    )
    comp = next(c for c in result["entities"]["components"] if c["id"] == "COMP-A")
    reqs = [p for p in comp["promises"] if p["attribute"] == "requirements"]
    # Verified preserved + doc-grounded added.
    contents = {p["content"] for p in reqs}
    assert "human authored" in contents
    assert "doc req" in contents


def test_ingest_requirements_does_not_mutate_input(tmp_path: Path, tiny_model):
    (tmp_path / "docs" / "reports").mkdir(parents=True)
    (tmp_path / "docs" / "reports" / "x.md").write_text(
        "## AuthService\n\n- r\n"
    )
    before = copy.deepcopy(tiny_model)
    ingest_requirements(tiny_model, repo_path=tmp_path, doc_roots=("docs/reports",))
    assert tiny_model == before


def test_ingest_requirements_deterministic(tmp_path: Path, tiny_model):
    (tmp_path / "docs" / "reports").mkdir(parents=True)
    (tmp_path / "docs" / "reports" / "x.md").write_text(
        "## AuthService\n\n- r1\n- r2\n"
    )
    a = ingest_requirements(tiny_model, repo_path=tmp_path, doc_roots=("docs/reports",))
    b = ingest_requirements(tiny_model, repo_path=tmp_path, doc_roots=("docs/reports",))
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_ingest_requirements_empty_body_no_promises(tmp_path: Path, tiny_model):
    (tmp_path / "docs" / "reports").mkdir(parents=True)
    (tmp_path / "docs" / "reports" / "x.md").write_text(
        "## AuthService\n\njust prose no bullets\n"
    )
    result = ingest_requirements(
        tiny_model, repo_path=tmp_path, doc_roots=("docs/reports",)
    )
    comp = next(c for c in result["entities"]["components"] if c["id"] == "COMP-A")
    assert not [p for p in comp["promises"] if p["attribute"] == "requirements"]


def test_ingest_requirements_no_provider_skips_layer3(tmp_path: Path, tiny_model):
    """When no provider passed, only Layers 1+2 fire."""
    (tmp_path / "docs" / "reports").mkdir(parents=True)
    # A heading that ONLY Layer 3 would match (fuzzy, not exact).
    (tmp_path / "docs" / "reports" / "pay.md").write_text(
        "## Payment Gateway Integration\n\n- r\n"
    )
    result = ingest_requirements(
        tiny_model, repo_path=tmp_path, doc_roots=("docs/reports",), provider=None
    )
    comp = next(c for c in result["entities"]["components"] if c["id"] == "COMP-B")
    assert not [p for p in comp["promises"] if p["attribute"] == "requirements"]
