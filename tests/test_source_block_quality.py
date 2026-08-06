"""Tests for F-block quality metrics."""

from architecture_model.core.source_block_quality import (
    FBlockProvenance,
    FBlockQuality,
    compute_agreement_rate,
    compute_conductance,
    compute_source_block_quality,
    compute_modularity,
    compute_provenance,
)
from architecture_model.core.types import (
    ArchitectureModel,
    Component,
    Entities,
    ModelMeta,
    Relationship,
    RelationType,
    Status,
)


def _make_model(components, relationships):
    return ArchitectureModel(
        meta=ModelMeta(schema_version="1.3", project="test"),
        entities=Entities(components=components),
        relationships=relationships,
    )


def _two_cluster_model():
    """Two well-separated clusters: {A,B} and {C,D}, one cross-edge."""
    comps = [
        Component(id="A", name="A", status=Status.ACTIVE, source_block="S1"),
        Component(id="B", name="B", status=Status.ACTIVE, source_block="S1"),
        Component(id="C", name="C", status=Status.ACTIVE, source_block="S2"),
        Component(id="D", name="D", status=Status.ACTIVE, source_block="S2"),
    ]
    rels = [
        Relationship(type=RelationType.DEPENDS_ON, from_id="A", to_id="B"),
        Relationship(type=RelationType.DEPENDS_ON, from_id="B", to_id="A"),
        Relationship(type=RelationType.DEPENDS_ON, from_id="C", to_id="D"),
        Relationship(type=RelationType.DEPENDS_ON, from_id="D", to_id="C"),
        # One cross-edge
        Relationship(type=RelationType.DEPENDS_ON, from_id="A", to_id="C"),
    ]
    return _make_model(comps, rels)


class TestModularity:
    def test_two_cluster_positive_q(self):
        model = _two_cluster_model()
        q = compute_modularity(model)
        assert q > 0.1, f"Expected Q > 0.1 for well-separated clusters, got {q}"

    def test_single_cluster_q_zero(self):
        comps = [
            Component(id="A", name="A", status=Status.ACTIVE, source_block="S1"),
            Component(id="B", name="B", status=Status.ACTIVE, source_block="S1"),
        ]
        rels = [
            Relationship(type=RelationType.DEPENDS_ON, from_id="A", to_id="B"),
        ]
        model = _make_model(comps, rels)
        q = compute_modularity(model)
        assert q == 0.0, f"Single cluster should have Q=0, got {q}"

    def test_no_edges_q_zero(self):
        comps = [
            Component(id="A", name="A", status=Status.ACTIVE, source_block="S1"),
            Component(id="B", name="B", status=Status.ACTIVE, source_block="S2"),
        ]
        model = _make_model(comps, [])
        q = compute_modularity(model)
        assert q == 0.0


class TestOrphanRate:
    def test_all_disconnected(self):
        comps = [
            Component(id="A", name="A", status=Status.ACTIVE, source_block="S1"),
            Component(id="B", name="B", status=Status.ACTIVE, source_block="S2"),
            Component(id="C", name="C", status=Status.ACTIVE, source_block="S3"),
        ]
        model = _make_model(comps, [])
        quality = compute_source_block_quality(model)
        assert quality.orphan_rate == 1.0


class TestCrossBlockCycleRatio:
    def test_bidirectional_cross_block(self):
        comps = [
            Component(id="A", name="A", status=Status.ACTIVE, source_block="S1"),
            Component(id="B", name="B", status=Status.ACTIVE, source_block="S2"),
        ]
        rels = [
            Relationship(type=RelationType.DEPENDS_ON, from_id="A", to_id="B"),
            Relationship(type=RelationType.DEPENDS_ON, from_id="B", to_id="A"),
        ]
        model = _make_model(comps, rels)
        quality = compute_source_block_quality(model)
        assert quality.cross_block_cycle_ratio > 0, "Bidirectional should have cycle_ratio > 0"


class TestClusterBalance:
    def test_balanced_clusters_low_gini(self):
        comps = [
            Component(id="A", name="A", status=Status.ACTIVE, source_block="S1"),
            Component(id="B", name="B", status=Status.ACTIVE, source_block="S1"),
            Component(id="C", name="C", status=Status.ACTIVE, source_block="S2"),
            Component(id="D", name="D", status=Status.ACTIVE, source_block="S2"),
        ]
        rels = [
            Relationship(type=RelationType.DEPENDS_ON, from_id="A", to_id="B"),
            Relationship(type=RelationType.DEPENDS_ON, from_id="C", to_id="D"),
        ]
        model = _make_model(comps, rels)
        quality = compute_source_block_quality(model)
        assert quality.cluster_balance < 0.2, f"Balanced clusters should have low Gini, got {quality.cluster_balance}"


class TestComputeFBlockQuality:
    def test_returns_valid_quality(self):
        model = _two_cluster_model()
        quality = compute_source_block_quality(model)
        assert isinstance(quality, FBlockQuality)
        assert isinstance(quality.modularity, float)
        assert isinstance(quality.conductance, dict)
        assert isinstance(quality.orphan_rate, float)
        assert 0.0 <= quality.orphan_rate <= 1.0


class TestProvenance:
    def test_provenance_computed_and_attached(self):
        model = _two_cluster_model()
        quality = compute_source_block_quality(model)
        provenance = compute_provenance(model, quality)
        assert len(provenance) == 4
        for comp in model.entities.components:
            assert comp.id in provenance
            prov = provenance[comp.id]
            assert isinstance(prov, FBlockProvenance)
            assert 0.0 <= prov.confidence <= 1.0
            assert prov.content_hash
            assert prov.computed_at
            # Check it's attached to extensions
            assert "source_block_provenance" in comp.extensions
            assert comp.extensions["source_block_provenance"]["confidence"] == prov.confidence


class TestAgreementRate:
    def test_agreement_with_matching_clustering(self):
        """When auto_assign produces the same partition, agreement should be 1.0."""
        # Build a model where auto_assign would group A-B together and C alone
        comps = [
            Component(id="A", name="A", status=Status.ACTIVE, source_block="S1"),
            Component(id="B", name="B", status=Status.ACTIVE, source_block="S1"),
            Component(id="C", name="C", status=Status.ACTIVE, source_block="S2"),
        ]
        rels = [
            Relationship(type=RelationType.DEPENDS_ON, from_id="A", to_id="B"),
        ]
        model = _make_model(comps, rels)
        rate = compute_agreement_rate(model)
        assert rate == 1.0, f"Expected 1.0, got {rate}"

    def test_disagreement_when_partitions_differ(self):
        """When manual source_blocks don't match clustering, agreement < 1.0."""
        # Force disagreement: put connected nodes in different blocks
        comps = [
            Component(id="A", name="A", status=Status.ACTIVE, source_block="S1"),
            Component(id="B", name="B", status=Status.ACTIVE, source_block="S2"),
            Component(id="C", name="C", status=Status.ACTIVE, source_block="S1"),
        ]
        rels = [
            Relationship(type=RelationType.DEPENDS_ON, from_id="A", to_id="B"),
            Relationship(type=RelationType.DEPENDS_ON, from_id="B", to_id="C"),
        ]
        model = _make_model(comps, rels)
        rate = compute_agreement_rate(model)
        assert rate < 1.0, f"Expected < 1.0 for disagreeing partitions, got {rate}"


class TestCoverageIntegration:
    def test_source_block_quality_in_coverage_report(self):
        from architecture_model.core.coverage import coverage_report

        model = _two_cluster_model()
        manifest = {"modules": [], "interfaces": [], "functional_blocks": {}}
        result = coverage_report(model, manifest)
        check_names = [c.name for c in result.checks]
        assert "F-Block Quality" in check_names, f"Missing F-Block Quality check in {check_names}"
        fb_check = next(c for c in result.checks if c.name == "F-Block Quality")
        assert 0 <= fb_check.score <= 100
