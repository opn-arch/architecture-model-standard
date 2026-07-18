from architecture_model.config.schema import DiscoveryReport, DiscoveryCandidate


def test_discovery_report_tracks_candidates():
    r = DiscoveryReport()
    r.add_candidate("source_root", "/src/pkg", accepted=True, reason="src-layout detected")
    r.add_candidate("source_root", "/lib/pkg", accepted=False, reason="checked after src-layout match")
    assert len(r.candidates) == 2
    assert r.candidates[0].accepted is True
    assert r.candidates[1].accepted is False


def test_discovery_report_summary():
    r = DiscoveryReport()
    r.layout_detected = "src-layout"
    r.blocks_discovered = 5
    r.layers_discovered = 3
    r.metrics_discovered = 2
    r.files_total = 100
    r.files_claimed = 85
    s = r.summary()
    assert "src-layout" in s
    assert "5 blocks" in s
