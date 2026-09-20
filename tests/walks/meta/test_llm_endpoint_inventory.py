"""Tests for llm_endpoint_inventory meta-walk. Realizes ``CAP-WK.llm-endpoint-inventory``.

Uses hermetic synthetic fixture repos (tmp_path-hosted directory trees
with hand-written Python source) — no dependency on the real AMS or
OCA source trees. Target runtime: <1s.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from architecture_model.walks.meta.llm_endpoint_inventory import (
    COVERED,
    LEGACY,
    STALE,
    UNDECLARED,
    EndpointCard,
    audit_llm_endpoints,
    load_declared_inventory,
    scan_repo,
)


# ---- fixture helpers -------------------------------------------------


def _make_repo(root: Path, name: str, files: dict[str, str]) -> Path:
    """Create ``root/name/src/<file>`` for each entry in files."""
    repo = root / name
    src = repo / "src"
    src.mkdir(parents=True, exist_ok=True)
    for relpath, content in files.items():
        target = src / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return repo


def _write_inventory(ams_root: Path, endpoints: list[dict]) -> None:
    ams_root.joinpath(".architecture", "llm").mkdir(parents=True, exist_ok=True)
    ams_root.joinpath(".architecture", "llm", "endpoints.yaml").write_text(
        yaml.safe_dump({"endpoints": endpoints}, sort_keys=False),
        encoding="utf-8",
    )


# ---- scan_repo -------------------------------------------------------


def test_scan_repo_detects_all_patterns(tmp_path: Path):
    ams = _make_repo(
        tmp_path,
        "architecture-model-standard",
        {
            "a/b.py": (
                "def x(provider, ctx, llm_callback):\n"
                "    provider.complete('p')\n"
                "    provider.structured('p', {})\n"
                "    provider.stream('p')\n"
                "    ctx.llm_enrich('p')\n"
                "    llm_callback('p')\n"
                "    provider.run_via_policy('p')\n"
            ),
        },
    )
    hits = scan_repo(ams)
    # 6 hits from a single file.
    assert len(hits) == 6
    patterns = {p for _eid, p, _ln in hits}
    assert patterns == {
        "complete",
        "structured",
        "stream",
        "llm_enrich",
        "llm_callback",
        "run_via_policy",
    }
    # All ids share the same relpath and repo slug.
    for eid, _pattern, _ln in hits:
        assert eid.startswith("architecture-model-standard:src/a/b.py:")


def test_scan_repo_skips_non_llm_calls(tmp_path: Path):
    ams = _make_repo(
        tmp_path,
        "architecture-model-standard",
        {
            "x.py": (
                "print('hi')\n"
                "obj.other_method()\n"
                "other_function()\n"
            ),
        },
    )
    assert scan_repo(ams) == []


def test_scan_repo_ignores_syntax_errors(tmp_path: Path):
    """A malformed file must not raise; the walk continues past it."""
    ams = _make_repo(
        tmp_path,
        "architecture-model-standard",
        {
            "broken.py": "def (:\n",  # syntax error
            "good.py": "provider.complete('p')\n",
        },
    )
    hits = scan_repo(ams)
    assert len(hits) == 1
    assert hits[0][1] == "complete"


def test_scan_repo_only_scans_src(tmp_path: Path):
    """Files outside ``src/`` are ignored."""
    repo = tmp_path / "architecture-model-standard"
    (repo / "src").mkdir(parents=True)
    (repo / "tests").mkdir(parents=True)
    (repo / "src" / "in.py").write_text("provider.complete('p')\n")
    (repo / "tests" / "out.py").write_text("provider.complete('p')\n")
    (repo / "scripts.py").write_text("provider.complete('p')\n")
    hits = scan_repo(repo)
    assert len(hits) == 1
    assert "src/in.py" in hits[0][0]


def test_scan_repo_missing_src_returns_empty(tmp_path: Path):
    """No ``src/`` directory → empty list, no raise."""
    repo = tmp_path / "empty-repo"
    repo.mkdir()
    assert scan_repo(repo) == []


# ---- load_declared_inventory -----------------------------------------


def test_load_inventory_missing_file(tmp_path: Path):
    assert load_declared_inventory(tmp_path) == []


def test_load_inventory_happy_path(tmp_path: Path):
    _write_inventory(
        tmp_path,
        [
            {"id": "repo:src/a.py:1", "kind": "completion", "migration_status": "protocol"},
        ],
    )
    inv = load_declared_inventory(tmp_path)
    assert len(inv) == 1
    assert inv[0]["id"] == "repo:src/a.py:1"


def test_load_inventory_malformed_yaml(tmp_path: Path):
    """Parse error → empty list, no raise."""
    tmp_path.joinpath(".architecture", "llm").mkdir(parents=True)
    tmp_path.joinpath(".architecture", "llm", "endpoints.yaml").write_text(
        "endpoints: [not: closed\n"
    )
    assert load_declared_inventory(tmp_path) == []


# ---- audit_llm_endpoints ---------------------------------------------


def test_audit_covered_verdict(tmp_path: Path):
    """AST hit + declared entry with protocol status → covered."""
    ams = _make_repo(
        tmp_path,
        "architecture-model-standard",
        {"m.py": "provider.complete('p')\n"},
    )
    _write_inventory(
        ams,
        [
            {
                "id": "architecture-model-standard:src/m.py:1",
                "kind": "completion",
                "migration_status": "protocol",
                "task_class": "enrichment",
                "tier": "T2",
            },
        ],
    )
    # Point oca to a definitely-missing path; missing-OCA emits a meta card
    # but doesn't affect AMS coverage.
    report = audit_llm_endpoints(ams, oca_root=tmp_path / "no-such-oca")
    real_cards = [c for c in report.cards if not c.endpoint_id.startswith("__meta__:")]
    assert len(real_cards) == 1
    assert real_cards[0].verdict == COVERED
    assert real_cards[0].details["pattern"] == "complete"
    assert real_cards[0].details["migration_status"] == "protocol"


def test_audit_legacy_verdict(tmp_path: Path):
    """AST hit + declared legacy → legacy (overrides covered)."""
    ams = _make_repo(
        tmp_path,
        "architecture-model-standard",
        {"m.py": "llm_callback('p')\n"},
    )
    _write_inventory(
        ams,
        [
            {
                "id": "architecture-model-standard:src/m.py:1",
                "kind": "review",
                "migration_status": "legacy",
            },
        ],
    )
    report = audit_llm_endpoints(ams, oca_root=tmp_path / "no-such-oca")
    real_cards = [c for c in report.cards if not c.endpoint_id.startswith("__meta__:")]
    assert len(real_cards) == 1
    assert real_cards[0].verdict == LEGACY


def test_audit_undeclared_verdict(tmp_path: Path):
    """AST hit, no declared entry → undeclared."""
    ams = _make_repo(
        tmp_path,
        "architecture-model-standard",
        {"m.py": "provider.complete('p')\n"},
    )
    # No inventory file at all.
    report = audit_llm_endpoints(ams, oca_root=tmp_path / "no-such-oca")
    real_cards = [c for c in report.cards if not c.endpoint_id.startswith("__meta__:")]
    assert len(real_cards) == 1
    assert real_cards[0].verdict == UNDECLARED
    assert real_cards[0].details["pattern"] == "complete"


def test_audit_stale_verdict(tmp_path: Path):
    """Declared entry, no AST hit → stale."""
    ams = _make_repo(
        tmp_path,
        "architecture-model-standard",
        {"m.py": "print('nothing')\n"},
    )
    _write_inventory(
        ams,
        [
            {
                "id": "architecture-model-standard:src/gone.py:42",
                "kind": "completion",
                "migration_status": "protocol",
            },
        ],
    )
    report = audit_llm_endpoints(ams, oca_root=tmp_path / "no-such-oca")
    real_cards = [c for c in report.cards if not c.endpoint_id.startswith("__meta__:")]
    assert len(real_cards) == 1
    assert real_cards[0].verdict == STALE


def test_audit_missing_oca_emits_meta_card(tmp_path: Path):
    """OCA sibling absent → __meta__:oca_missing card, no raise."""
    ams = _make_repo(
        tmp_path,
        "architecture-model-standard",
        {"m.py": "pass\n"},
    )
    report = audit_llm_endpoints(ams, oca_root=tmp_path / "definitely-missing")
    meta_cards = [c for c in report.cards if c.endpoint_id.startswith("__meta__:")]
    assert len(meta_cards) == 1
    assert meta_cards[0].endpoint_id == "__meta__:oca_missing"


def test_audit_cross_repo_hits(tmp_path: Path):
    """Both AMS and OCA hits appear in the same report."""
    ams = _make_repo(
        tmp_path,
        "architecture-model-standard",
        {"m.py": "provider.complete('p')\n"},
    )
    oca = _make_repo(
        tmp_path,
        "opencode-arch",
        {"tool.py": "provider.structured('p', {})\n"},
    )
    report = audit_llm_endpoints(ams, oca_root=oca)
    ids = {c.endpoint_id for c in report.cards}
    assert any(eid.startswith("architecture-model-standard:") for eid in ids)
    assert any(eid.startswith("opencode-arch:") for eid in ids)


def test_audit_deterministic_ordering(tmp_path: Path):
    """Same inputs → same card order."""
    ams = _make_repo(
        tmp_path,
        "architecture-model-standard",
        {
            "b.py": "provider.complete('p')\n",
            "a.py": "provider.structured('p', {})\n",
        },
    )
    r1 = audit_llm_endpoints(ams, oca_root=tmp_path / "no-such-oca")
    r2 = audit_llm_endpoints(ams, oca_root=tmp_path / "no-such-oca")
    assert [c.endpoint_id for c in r1.cards] == [c.endpoint_id for c in r2.cards]


def test_audit_default_oca_path(tmp_path: Path):
    """Default oca_root = ams_root.parent / 'opencode-arch'."""
    ams = _make_repo(tmp_path, "architecture-model-standard", {"m.py": "pass\n"})
    _make_repo(tmp_path, "opencode-arch", {"tool.py": "provider.complete('p')\n"})
    report = audit_llm_endpoints(ams)  # no oca_root override
    # No __meta__ card — sibling was found.
    assert not any(c.endpoint_id.startswith("__meta__:") for c in report.cards)
    ids = {c.endpoint_id for c in report.cards}
    assert any(eid.startswith("opencode-arch:") for eid in ids)


def test_audit_report_counts(tmp_path: Path):
    """declared_count and ast_hit_count reflect inputs."""
    ams = _make_repo(
        tmp_path,
        "architecture-model-standard",
        {"m.py": "provider.complete('p')\nprovider.structured('p', {})\n"},
    )
    _write_inventory(
        ams,
        [
            {"id": "architecture-model-standard:src/m.py:1", "migration_status": "protocol"},
            {"id": "architecture-model-standard:src/m.py:2", "migration_status": "protocol"},
            {"id": "architecture-model-standard:src/gone.py:1", "migration_status": "protocol"},
        ],
    )
    report = audit_llm_endpoints(ams, oca_root=tmp_path / "no-such-oca")
    assert report.declared_count == 3
    assert report.ast_hit_count == 2


def test_endpoint_card_to_dict_via_report(tmp_path: Path):
    """InventoryReport.to_dict() emits nested Card dicts."""
    ams = _make_repo(
        tmp_path,
        "architecture-model-standard",
        {"m.py": "provider.complete('p')\n"},
    )
    report = audit_llm_endpoints(ams, oca_root=tmp_path / "no-such-oca")
    data = report.to_dict()
    assert "cards" in data
    assert "declared_count" in data
    assert "ast_hit_count" in data
    assert isinstance(data["cards"], list)
    assert all("endpoint_id" in c and "verdict" in c for c in data["cards"])
