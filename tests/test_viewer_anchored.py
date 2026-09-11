"""Track 4 Pass 1 Task 5 — functional panel renders only anchor.model entities."""
from pathlib import Path

from architecture_model.core.parser import load_model
from architecture_model.core.visualize import generate_html_viewer
from architecture_model.core.slice_anchor import build_slice_anchor, VIEW_TO_ARTIFACT


def _model_yaml(path: Path) -> Path:
    """Model: CAP-1 realized by COMP-1 (both in-scope for functional). LAY-9 is unrelated."""
    path.write_text("""
meta:
  project: t
  schema_version: '2.1'
entities:
  capabilities:
    - id: CAP-1
      name: InScopeCap
  components:
    - id: COMP-1
      name: InScopeComp
      source_files: [src/a.py]
  layers:
    - id: LAY-9
      name: UnrelatedLayerNAME
relationships:
  - from: COMP-1
    to: CAP-1
    type: realizes
""".lstrip())
    return path


def test_functional_panel_renders_only_anchored_entities(tmp_path):
    model_path = _model_yaml(tmp_path / ".architecture-model.yaml")
    model = load_model(model_path)
    anchors = {v: build_slice_anchor(model, v, tmp_path) for v in VIEW_TO_ARTIFACT}
    out = tmp_path / "viewer.html"
    generate_html_viewer(model, out, repo_path=tmp_path, anchors=anchors)
    html = out.read_text(encoding="utf-8")

    assert "InScopeCap" in html
    from architecture_model.core.visualize import generate_functional_architecture_diagram
    functional_body = generate_functional_architecture_diagram(anchors["functional"].model)
    assert "UnrelatedLayerNAME" not in functional_body


def test_functional_panel_without_anchors_still_uses_full_model(tmp_path):
    model_path = _model_yaml(tmp_path / ".architecture-model.yaml")
    model = load_model(model_path)
    out = tmp_path / "viewer.html"
    generate_html_viewer(model, out, repo_path=tmp_path)
    html = out.read_text(encoding="utf-8")
    assert "InScopeCap" in html


# --- Regression: end-to-end proof that generate_html_viewer routes the
# functional panel through anchor.model (Track 4 Pass 1 Task 5) ---

def _full_model_with_exclusive_cap(path: Path) -> Path:
    """Full model: CAP-0 -> CAP-EXCL-FULL and CAP-0 -> CAP-IN-SLICE via
    'contains'. CAP-EXCL-FULL will render into the functional panel body
    (it's a direct child of root CAP-0).
    """
    path.write_text("""
meta:
  project: t
  schema_version: '2.1'
entities:
  capabilities:
    - id: CAP-0
      name: Root
    - id: CAP-IN-SLICE
      name: KeepMeCap
    - id: CAP-EXCL-FULL
      name: ExclusiveOnlyInFullXYZZY
  components:
    - id: COMP-1
      name: KeepMeComp
      source_files: [src/a.py]
relationships:
  - from: CAP-0
    to: CAP-IN-SLICE
    type: contains
  - from: CAP-0
    to: CAP-EXCL-FULL
    type: contains
  - from: COMP-1
    to: CAP-IN-SLICE
    type: realizes
""".lstrip())
    return path


def _subset_model_yaml(path: Path) -> Path:
    """Anchored subset: excludes CAP-EXCL-FULL and its contains edge."""
    path.write_text("""
meta:
  project: t
  schema_version: '2.1'
entities:
  capabilities:
    - id: CAP-0
      name: Root
    - id: CAP-IN-SLICE
      name: KeepMeCap
  components:
    - id: COMP-1
      name: KeepMeComp
      source_files: [src/a.py]
relationships:
  - from: CAP-0
    to: CAP-IN-SLICE
    type: contains
  - from: COMP-1
    to: CAP-IN-SLICE
    type: realizes
""".lstrip())
    return path


def test_generate_html_viewer_routes_functional_panel_through_anchor_model(tmp_path):
    """End-to-end regression: the exclusive capability MUST NOT appear in the
    generated HTML when a SliceAnchor whose .model excludes it is passed for
    the 'functional' view. Sanity companion: without anchors, it DOES appear.

    Constructs SliceAnchor directly (bypassing build_slice_anchor) so the
    1-hop closure over the CAP-0 contains edge cannot pull CAP-EXCL-FULL
    back into the anchor's model.
    """
    from architecture_model.core.slice_anchor import SliceAnchor

    full_path = _full_model_with_exclusive_cap(tmp_path / ".architecture-model.yaml")
    subset_path = _subset_model_yaml(tmp_path / "subset.yaml")
    full_model = load_model(full_path)
    subset_model = load_model(subset_path)

    anchor = SliceAnchor(
        view_name="functional",
        artifact_name="functional-architecture",
        model=subset_model,
        files=(),
        artifacts=(),
    )

    # With anchor: functional panel body is rebuilt from anchor.model, so
    # references to the excluded id drop dramatically. Without anchor, the
    # full-model functional panel embeds CAP-EXCL-FULL throughout the
    # Mermaid body (node decl, edges, class assignments, panel JSON, etc.).
    out_anchored = tmp_path / "viewer_anchored.html"
    generate_html_viewer(
        full_model, out_anchored, repo_path=tmp_path,
        anchors={"functional": anchor},
    )
    html_anchored = out_anchored.read_text(encoding="utf-8")

    # Sanity companion: without anchors, the full model is used everywhere.
    out_full = tmp_path / "viewer_full.html"
    generate_html_viewer(full_model, out_full, repo_path=tmp_path, anchors=None)
    html_full = out_full.read_text(encoding="utf-8")

    # Discriminating evidence for routing: the excluded entity's id appears
    # far fewer times in the anchored HTML than in the full-model HTML.
    # (Pre-Task-5 code produces equal counts — the anchor is ignored.)
    anchored_count = html_anchored.count("CAP-EXCL-FULL")
    full_count = html_full.count("CAP-EXCL-FULL")
    assert anchored_count < full_count, (
        f"Functional panel is not routed through anchor.model: "
        f"CAP-EXCL-FULL occurrences anchored={anchored_count} vs "
        f"full={full_count} (expected strictly less when routing is active)."
    )
    # Sanity: subset entity is still present in the anchored HTML.
    assert "KeepMeCap" in html_anchored
    # Sanity: exclusive entity IS present without the anchor, proving the
    # discriminator above is meaningful (fixture not trivially broken).
    assert full_count > 0


# --- Track 4 Pass 2 Task T7a: anchor routing extended to `logical` panel ---

def _full_model_with_exclusive_comp(path: Path) -> Path:
    """Full model: two components, COMP-KEEP-LOG and COMP-EXCL-LOG."""
    path.write_text("""
meta:
  project: t
  schema_version: '2.1'
entities:
  components:
    - id: COMP-KEEP-LOG
      name: KeepMeCompLog
      source_files: [src/a.py]
    - id: COMP-EXCL-LOG
      name: ExcludedCompLogXYZZY
      source_files: [src/b.py]
""".lstrip())
    return path


def _subset_model_yaml_logical(path: Path) -> Path:
    """Anchored subset: excludes COMP-EXCL-LOG."""
    path.write_text("""
meta:
  project: t
  schema_version: '2.1'
entities:
  components:
    - id: COMP-KEEP-LOG
      name: KeepMeCompLog
      source_files: [src/a.py]
""".lstrip())
    return path


def test_generate_html_viewer_routes_logical_panel_through_anchor_model(tmp_path):
    """End-to-end regression: the excluded component MUST NOT appear (or
    must appear strictly fewer times) in the generated HTML when a
    SliceAnchor whose .model excludes it is passed for the 'logical' view.
    """
    from architecture_model.core.slice_anchor import SliceAnchor

    full_path = _full_model_with_exclusive_comp(tmp_path / ".architecture-model.yaml")
    subset_path = _subset_model_yaml_logical(tmp_path / "subset_logical.yaml")
    full_model = load_model(full_path)
    subset_model = load_model(subset_path)

    anchor = SliceAnchor(
        view_name="logical",
        artifact_name="logical-architecture",
        model=subset_model,
        files=(),
        artifacts=(),
    )

    out_anchored = tmp_path / "viewer_anchored_logical.html"
    generate_html_viewer(
        full_model, out_anchored, repo_path=tmp_path,
        anchors={"logical": anchor},
    )
    html_anchored = out_anchored.read_text(encoding="utf-8")

    out_full = tmp_path / "viewer_full_logical.html"
    generate_html_viewer(full_model, out_full, repo_path=tmp_path, anchors=None)
    html_full = out_full.read_text(encoding="utf-8")

    anchored_count = html_anchored.count("COMP-EXCL-LOG")
    full_count = html_full.count("COMP-EXCL-LOG")
    assert anchored_count < full_count, (
        f"Logical panel is not routed through anchor.model: "
        f"COMP-EXCL-LOG occurrences anchored={anchored_count} vs "
        f"full={full_count} (expected strictly less when routing is active)."
    )
    assert "KeepMeCompLog" in html_anchored
    assert full_count > 0


# --- Track 4 Pass 2 Task T7b: conops panel routed through anchor.model ---

def _full_model_with_exclusive_conops_cap(path: Path) -> Path:
    """Full model: actor + two behaviors. Behaviors render as scenario
    nodes in the conops panel body, so BEH-EXCL-CON's id appears in the
    Mermaid body when the full model is rendered.

    (Capabilities do not surface in the curated ConOps projector body,
    so anchor-driven capability exclusion would be invisible in the
    generated HTML — behaviors are the right entity kind to exclude.)
    """
    path.write_text("""
meta:
  project: t
  schema_version: '2.1'
entities:
  actors:
    - id: ACT-1
      name: Operator
  behaviors:
    - id: BEH-KEEP-CON
      name: KeepMeBehCon
      actor_id: ACT-1
    - id: BEH-EXCL-CON
      name: ExcludedBehConXYZZY
      actor_id: ACT-1
relationships:
  - from: ACT-1
    to: BEH-KEEP-CON
    type: triggers
  - from: ACT-1
    to: BEH-EXCL-CON
    type: triggers
""".lstrip())
    return path


def _subset_model_yaml_conops(path: Path) -> Path:
    """Anchored subset: excludes BEH-EXCL-CON and its triggers edge."""
    path.write_text("""
meta:
  project: t
  schema_version: '2.1'
entities:
  actors:
    - id: ACT-1
      name: Operator
  behaviors:
    - id: BEH-KEEP-CON
      name: KeepMeBehCon
      actor_id: ACT-1
relationships:
  - from: ACT-1
    to: BEH-KEEP-CON
    type: triggers
""".lstrip())
    return path


def test_generate_html_viewer_routes_conops_panel_through_anchor_model(tmp_path):
    """End-to-end regression: the excluded behavior MUST appear strictly
    fewer times in the generated HTML when a SliceAnchor whose .model
    excludes it is passed for the 'conops' view.
    """
    from architecture_model.core.slice_anchor import SliceAnchor

    full_path = _full_model_with_exclusive_conops_cap(tmp_path / ".architecture-model.yaml")
    subset_path = _subset_model_yaml_conops(tmp_path / "subset_conops.yaml")
    full_model = load_model(full_path)
    subset_model = load_model(subset_path)

    anchor = SliceAnchor(
        view_name="conops",
        artifact_name="conops",
        model=subset_model,
        files=(),
        artifacts=(),
    )

    out_anchored = tmp_path / "viewer_anchored_conops.html"
    generate_html_viewer(
        full_model, out_anchored, repo_path=tmp_path,
        anchors={"conops": anchor},
    )
    html_anchored = out_anchored.read_text(encoding="utf-8")

    out_full = tmp_path / "viewer_full_conops.html"
    generate_html_viewer(full_model, out_full, repo_path=tmp_path, anchors=None)
    html_full = out_full.read_text(encoding="utf-8")

    anchored_count = html_anchored.count("BEH-EXCL-CON")
    full_count = html_full.count("BEH-EXCL-CON")
    assert anchored_count < full_count, (
        f"ConOps panel is not routed through anchor.model: "
        f"BEH-EXCL-CON occurrences anchored={anchored_count} vs "
        f"full={full_count} (expected strictly less when routing is active)."
    )
    assert "KeepMeBehCon" in html_anchored
    assert full_count > 0


# --- Track 4 Pass 2 Task T7c: use_cases panel routed through anchor.model ---

def _full_model_with_exclusive_behavior(path: Path) -> Path:
    """Full model has two behaviors both attributed to the same actor;
    both render into the use_cases panel."""
    path.write_text("""
meta:
  project: t
  schema_version: '2.1'
entities:
  actors:
    - id: ACT-1
      name: Operator
  behaviors:
    - id: BEH-IN-UC
      name: KeepMeUseCase
      actor: Operator
    - id: BEH-EXCL-UC
      name: ExcludedUseCaseXYZZY
      actor: Operator
""".lstrip())
    return path


def _subset_model_no_exclusive_behavior(path: Path) -> Path:
    """Anchored subset excludes BEH-EXCL-UC."""
    path.write_text("""
meta:
  project: t
  schema_version: '2.1'
entities:
  actors:
    - id: ACT-1
      name: Operator
  behaviors:
    - id: BEH-IN-UC
      name: KeepMeUseCase
      actor: Operator
""".lstrip())
    return path


def test_generate_html_viewer_routes_use_cases_panel_through_anchor_model(tmp_path):
    """End-to-end regression: the excluded behavior MUST appear strictly
    fewer times in the generated HTML when a SliceAnchor whose .model
    excludes it is passed for the 'use_cases' view.
    """
    from architecture_model.core.slice_anchor import SliceAnchor

    full_path = _full_model_with_exclusive_behavior(tmp_path / ".architecture-model.yaml")
    subset_path = _subset_model_no_exclusive_behavior(tmp_path / "subset_uc.yaml")
    full_model = load_model(full_path)
    subset_model = load_model(subset_path)

    anchor = SliceAnchor(
        view_name="use_cases",
        artifact_name="use-cases",
        model=subset_model,
        files=(),
        artifacts=(),
    )

    out_anchored = tmp_path / "viewer_anchored_uc.html"
    generate_html_viewer(
        full_model, out_anchored, repo_path=tmp_path,
        anchors={"use_cases": anchor},
    )
    html_anchored = out_anchored.read_text(encoding="utf-8")

    out_full = tmp_path / "viewer_full_uc.html"
    generate_html_viewer(full_model, out_full, repo_path=tmp_path, anchors=None)
    html_full = out_full.read_text(encoding="utf-8")

    anchored_count = html_anchored.count("BEH-EXCL-UC")
    full_count = html_full.count("BEH-EXCL-UC")
    assert anchored_count < full_count, (
        f"Use-cases panel is not routed through anchor.model: "
        f"BEH-EXCL-UC occurrences anchored={anchored_count} vs "
        f"full={full_count} (expected strictly less when routing is active)."
    )
    assert "KeepMeUseCase" in html_anchored
    assert full_count > 0


# --- Track 4 Pass 2 Task T7c: use_cases panel routed through anchor.model ---

def _full_model_with_exclusive_behavior(path: Path) -> Path:
    """Full model has two behaviors both attributed to the same actor;
    both render into the use_cases panel."""
    path.write_text("""
meta:
  project: t
  schema_version: '2.1'
entities:
  actors:
    - id: ACT-1
      name: Operator
  behaviors:
    - id: BEH-IN-UC
      name: KeepMeUseCase
      actor: Operator
    - id: BEH-EXCL-UC
      name: ExcludedUseCaseXYZZY
      actor: Operator
""".lstrip())
    return path


def _subset_model_no_exclusive_behavior(path: Path) -> Path:
    """Anchored subset excludes BEH-EXCL-UC."""
    path.write_text("""
meta:
  project: t
  schema_version: '2.1'
entities:
  actors:
    - id: ACT-1
      name: Operator
  behaviors:
    - id: BEH-IN-UC
      name: KeepMeUseCase
      actor: Operator
""".lstrip())
    return path


def test_generate_html_viewer_routes_use_cases_panel_through_anchor_model(tmp_path):
    """End-to-end regression: the excluded behavior MUST appear strictly
    fewer times in the generated HTML when a SliceAnchor whose .model
    excludes it is passed for the 'use_cases' view.
    """
    from architecture_model.core.slice_anchor import SliceAnchor

    full_path = _full_model_with_exclusive_behavior(tmp_path / ".architecture-model.yaml")
    subset_path = _subset_model_no_exclusive_behavior(tmp_path / "subset_uc.yaml")
    full_model = load_model(full_path)
    subset_model = load_model(subset_path)

    anchor = SliceAnchor(
        view_name="use_cases",
        artifact_name="use-cases",
        model=subset_model,
        files=(),
        artifacts=(),
    )

    out_anchored = tmp_path / "viewer_anchored_uc.html"
    generate_html_viewer(
        full_model, out_anchored, repo_path=tmp_path,
        anchors={"use_cases": anchor},
    )
    html_anchored = out_anchored.read_text(encoding="utf-8")

    out_full = tmp_path / "viewer_full_uc.html"
    generate_html_viewer(full_model, out_full, repo_path=tmp_path, anchors=None)
    html_full = out_full.read_text(encoding="utf-8")

    anchored_count = html_anchored.count("BEH-EXCL-UC")
    full_count = html_full.count("BEH-EXCL-UC")
    assert anchored_count < full_count, (
        f"Use-cases panel is not routed through anchor.model: "
        f"BEH-EXCL-UC occurrences anchored={anchored_count} vs "
        f"full={full_count} (expected strictly less when routing is active)."
    )
    assert "KeepMeUseCase" in html_anchored
    assert full_count > 0
