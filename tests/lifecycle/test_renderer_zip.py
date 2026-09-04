"""Tests for the ZIP bundle artifact renderer (T18 commit 2)."""
from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path

import pytest

from architecture_model.lifecycle.artifact_spec import ArtifactSpec
from architecture_model.lifecycle.renderers import DEFAULT_RENDERERS, get_renderer
from architecture_model.lifecycle.renderers.zip import (
    BundleResolutionError,
    render_zip,
)


def _make_zip_artifact(bundle_refs=("a1", "a2")) -> ArtifactSpec:
    return ArtifactSpec(
        id="a.bundle",
        renderer="zip",
        bundle_refs=list(bundle_refs),
    )


def _resolver_from(payloads: dict[str, bytes]):
    def _resolve(ref_id: str) -> bytes:
        if ref_id not in payloads:
            raise KeyError(ref_id)
        return payloads[ref_id]

    return _resolve


def test_render_zip_requires_resolver():
    with pytest.raises(ValueError, match="resolve_artifact"):
        render_zip([], _make_zip_artifact(), resolve_artifact=None)


def test_render_zip_rejects_wrong_renderer():
    # ArtifactSpec forbids non-zip renderer with bundle_refs; craft an html
    # artifact and pass to render_zip to check the renderer-name guard.
    from architecture_model.lifecycle.artifact_spec import ViewRef

    bogus = ArtifactSpec(
        id="a.wrong",
        renderer="html",
        view_ref=ViewRef(view_id="v.x", model_revision="r-1"),
    )
    with pytest.raises(ValueError, match="renderer mismatch"):
        render_zip([], bogus, resolve_artifact=_resolver_from({}))


def test_render_zip_missing_bundle_raises():
    artifact = _make_zip_artifact(("a1", "missing"))
    with pytest.raises(BundleResolutionError, match="missing"):
        render_zip([], artifact, resolve_artifact=_resolver_from({"a1": b"one"}))


def test_render_zip_resolver_returning_none_raises():
    def resolver(ref_id: str):
        return None

    with pytest.raises(BundleResolutionError):
        render_zip([], _make_zip_artifact(("a1",)), resolve_artifact=resolver)


def test_render_zip_builds_valid_archive_with_manifest():
    payloads = {"a1": b"payload-one", "a2": b"payload-two"}
    artifact = _make_zip_artifact(("a1", "a2"))
    result = render_zip([], artifact, resolve_artifact=_resolver_from(payloads))

    with zipfile.ZipFile(io.BytesIO(result), "r") as zf:
        names = sorted(zf.namelist())
        assert names == ["artifacts/a1", "artifacts/a2", "manifest.json"]
        assert zf.read("artifacts/a1") == b"payload-one"
        assert zf.read("artifacts/a2") == b"payload-two"
        manifest = json.loads(zf.read("manifest.json"))

    assert manifest["artifact_id"] == "a.bundle"
    assert manifest["renderer"] == "zip"
    assert manifest["contract_version"] == artifact.contract_version
    assert "artifact_digest" in manifest and manifest["artifact_digest"]
    assert "produced_at" in manifest
    bundles = manifest["bundles"]
    assert len(bundles) == 2
    assert [b["id"] for b in bundles] == ["a1", "a2"]  # sorted
    assert bundles[0]["path"] == "artifacts/a1"
    assert bundles[0]["sha256"] == hashlib.sha256(b"payload-one").hexdigest()
    assert bundles[1]["sha256"] == hashlib.sha256(b"payload-two").hexdigest()


def test_render_zip_bundles_sorted_when_input_unsorted():
    payloads = {"b": b"B", "a": b"A"}
    artifact = _make_zip_artifact(("b", "a"))
    result = render_zip([], artifact, resolve_artifact=_resolver_from(payloads))
    with zipfile.ZipFile(io.BytesIO(result), "r") as zf:
        manifest = json.loads(zf.read("manifest.json"))
    assert [b["id"] for b in manifest["bundles"]] == ["a", "b"]


def test_render_zip_deterministic_with_frozen_time(monkeypatch):
    import architecture_model.lifecycle.renderers.zip as zip_mod

    class _FrozenDatetime:
        @classmethod
        def now(cls, tz=None):
            from datetime import datetime as _real, timezone

            return _real(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)

    monkeypatch.setattr(zip_mod, "datetime", _FrozenDatetime)

    payloads = {"a1": b"one", "a2": b"two"}
    artifact = _make_zip_artifact(("a1", "a2"))
    r1 = render_zip([], artifact, resolve_artifact=_resolver_from(payloads))
    r2 = render_zip([], artifact, resolve_artifact=_resolver_from(payloads))
    assert r1 == r2


def test_render_zip_pure_no_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    before = set(Path(tmp_path).iterdir())
    render_zip(
        [],
        _make_zip_artifact(("a1",)),
        resolve_artifact=_resolver_from({"a1": b"x"}),
    )
    assert set(Path(tmp_path).iterdir()) == before


def test_zip_registered_in_defaults():
    assert "zip" in DEFAULT_RENDERERS
    assert get_renderer("zip") is render_zip


def test_zip_via_registry_signature_raises_without_resolver():
    # Calling via the (view, artifact) convention raises because resolver
    # cannot be supplied — this is the documented registry-call behavior.
    fn = get_renderer("zip")
    with pytest.raises(ValueError, match="resolve_artifact"):
        fn([], _make_zip_artifact(("a1",)))
