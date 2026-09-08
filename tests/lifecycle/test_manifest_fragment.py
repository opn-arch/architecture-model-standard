"""Tests for MaterializedSlice.manifest_fragment (Phase 2 Task 9)."""
from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from architecture_model.lifecycle.model_slice import (
    Curation,
    ModelSlice,
    Selectors,
    SupplementaryRef,
)
from architecture_model.lifecycle.model_slice_materializer import (
    ManifestFragment,
    materialize,
)
from architecture_model.lifecycle.package import load_package


ROOT_MODEL = dedent(
    """\
    meta:
      schema_version: '2.1.0'
      project: root
    entities:
      components:
        - id: COMP-A
          name: Alpha
          status: ACTIVE
          layer: core
          files:
            - src/core/alpha.py
        - id: COMP-B
          name: Bravo
          status: ACTIVE
          layer: web
          files:
            - src/web/bravo.py
    relationships: []
    """
)

PKG_YAML = dedent(
    """\
    architecture_id: root-pkg
    name: Root
    slug: root-pkg
    contract_version: "1.0.0"
    model_ref: .architecture-model.yaml
    manifest_ref: manifest.json
    """
)

ALPHA_PY = dedent(
    '''\
    """Alpha module."""

    ALPHA_CONST = 1


    def alpha_one(x: int) -> int:
        """First alpha function."""
        return x + 1


    def alpha_two(y: str) -> str:
        return y.upper()


    class AlphaClass:
        """Alpha class docstring."""

        def method_a(self) -> None:
            pass
    '''
)

BRAVO_PY = dedent(
    '''\
    """Bravo module."""

    from src.core import alpha


    def bravo_one() -> int:
        return alpha.alpha_one(0)


    class BravoClass:
        pass
    '''
)


@pytest.fixture
def pkg_with_code(tmp_path: Path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "package.yaml").write_text(PKG_YAML)
    (root / ".architecture-model.yaml").write_text(ROOT_MODEL)
    (root / "manifest.json").write_text("{}")
    core_dir = root / "src" / "core"
    core_dir.mkdir(parents=True)
    (core_dir / "alpha.py").write_text(ALPHA_PY)
    (core_dir / "__init__.py").write_text("")
    web_dir = root / "src" / "web"
    web_dir.mkdir(parents=True)
    (web_dir / "bravo.py").write_text(BRAVO_PY)
    (web_dir / "__init__.py").write_text("")
    (root / "src" / "__init__.py").write_text("")
    return load_package(root)


def _slice(**overrides):
    kwargs = dict(
        id="s1",
        architecture_id="root-pkg",
        model_revision="rev-1",
        scope="local",
        closure="strict",
        shared_refs="none",
        selectors=Selectors(entity_ids=["COMP-A"]),
        curation=Curation(),
    )
    kwargs.update(overrides)
    return ModelSlice(**kwargs)


# ---------------------------------------------------------------------------
# No supplementary ref → fragment stays None
# ---------------------------------------------------------------------------

def test_no_manifest_ref_leaves_fragment_none(pkg_with_code):
    slc = _slice()
    ms = materialize(slc, pkg_with_code)
    assert ms.manifest_fragment is None


# ---------------------------------------------------------------------------
# manifest ref populates fragment
# ---------------------------------------------------------------------------

def test_manifest_ref_populates_fragment(pkg_with_code):
    slc = _slice(
        supplementary_refs=(SupplementaryRef(kind="manifest"),),
    )
    ms = materialize(slc, pkg_with_code)
    frag = ms.manifest_fragment
    assert frag is not None
    assert isinstance(frag, ManifestFragment)
    # Only COMP-A is in-scope → only alpha.py should appear
    assert len(frag.modules) == 1
    assert frag.modules[0].file == "src/core/alpha.py"
    assert len(frag.functions) >= 2
    assert all(fn.file == "src/core/alpha.py" for fn in frag.functions)
    assert {fn.info.name for fn in frag.functions} >= {"alpha_one", "alpha_two"}


def test_manifest_fragment_scoped_by_component_files(pkg_with_code):
    """Slice selecting both components exposes both files' functions."""
    slc = _slice(
        selectors=Selectors(entity_ids=["COMP-A", "COMP-B"]),
        supplementary_refs=(SupplementaryRef(kind="manifest"),),
    )
    ms = materialize(slc, pkg_with_code)
    frag = ms.manifest_fragment
    assert frag is not None
    files = {m.file for m in frag.modules}
    assert files == {"src/core/alpha.py", "src/web/bravo.py"}
    fn_files = {fn.file for fn in frag.functions}
    assert fn_files == {"src/core/alpha.py", "src/web/bravo.py"}


def test_manifest_fragment_captures_classes(pkg_with_code):
    slc = _slice(
        selectors=Selectors(entity_ids=["COMP-A"]),
        supplementary_refs=(SupplementaryRef(kind="manifest"),),
    )
    ms = materialize(slc, pkg_with_code)
    frag = ms.manifest_fragment
    class_names = {c.info.name for c in frag.classes}
    assert "AlphaClass" in class_names
    assert all(c.file == "src/core/alpha.py" for c in frag.classes)


def test_manifest_fragment_imports_filtered_to_scope(pkg_with_code):
    """Only imports whose source AND target are in-scope files are kept."""
    slc_narrow = _slice(
        selectors=Selectors(entity_ids=["COMP-B"]),
        supplementary_refs=(SupplementaryRef(kind="manifest"),),
    )
    ms = materialize(slc_narrow, pkg_with_code)
    # bravo.py imports src.core.alpha but alpha.py is out of scope,
    # so no cross-file import edge should be retained.
    assert ms.manifest_fragment is not None
    imports_targets = {e.target for e in ms.manifest_fragment.imports}
    assert "src/core/alpha.py" not in imports_targets


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_manifest_ref_with_no_component_files_yields_empty_fragment(pkg_with_code):
    """Slice that selects zero components produces an empty (but non-None) fragment."""
    slc = _slice(
        selectors=Selectors(entity_kinds=["layer"]),
        supplementary_refs=(SupplementaryRef(kind="manifest"),),
    )
    ms = materialize(slc, pkg_with_code)
    frag = ms.manifest_fragment
    assert frag is not None
    assert frag.modules == ()
    assert frag.functions == ()
    assert frag.classes == ()


def test_manifest_fragment_is_frozen(pkg_with_code):
    slc = _slice(supplementary_refs=(SupplementaryRef(kind="manifest"),))
    ms = materialize(slc, pkg_with_code)
    with pytest.raises(Exception):
        ms.manifest_fragment.modules = ()  # type: ignore[misc]


def test_manifest_fragment_deterministic_ordering(pkg_with_code):
    """Two materializations of the same slice yield identical fragments."""
    slc = _slice(
        selectors=Selectors(entity_ids=["COMP-A", "COMP-B"]),
        supplementary_refs=(SupplementaryRef(kind="manifest"),),
    )
    ms1 = materialize(slc, pkg_with_code)
    ms2 = materialize(slc, pkg_with_code)
    files1 = [m.file for m in ms1.manifest_fragment.modules]
    files2 = [m.file for m in ms2.manifest_fragment.modules]
    assert files1 == files2
    # Modules must be sorted by file
    assert files1 == sorted(files1)
