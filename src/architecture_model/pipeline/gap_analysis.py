"""Gap analysis engine: diffs deterministic pipeline output vs LLM alternatives."""
from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Callable, Optional


# --- Generic name detection ---

_GENERIC_NAMES = frozenset({
    "main", "core", "utils", "helper", "misc", "common", "base",
    "default", "manager", "handler", "service", "helpers", "utilities",
})


def is_generic_name(name: str) -> bool:
    """Return True if *name* is a single-word generic/file-stem-like name."""
    stripped = name.strip()
    # Multi-word names with spaces are descriptive, not generic
    if " " in stripped:
        return False
    return stripped.lower() in _GENERIC_NAMES


# --- Data structures ---

@dataclass
class StageGap:
    """Gap between deterministic and LLM output for one stage."""
    stage: str
    deterministic: dict
    llm_alternative: dict
    added: list[dict] = field(default_factory=list)
    removed: list[dict] = field(default_factory=list)
    renamed: list[dict] = field(default_factory=list)
    quality_delta: float = 0.0


@dataclass
class NamingChain:
    """Traces how a source name propagates through stages."""
    source: str
    stages: dict[str, str] = field(default_factory=dict)
    llm_stages: dict[str, str] = field(default_factory=dict)
    is_generic: bool = False


@dataclass
class PropagationTrace:
    """Tracks how an error in stage N propagates to later stages."""
    origin_stage: str
    origin_entity: str
    origin_issue: str
    affected: list[dict] = field(default_factory=list)


@dataclass
class GapAnalysisResult:
    """Complete gap analysis result."""
    repo_path: str
    stage_gaps: list[StageGap] = field(default_factory=list)
    naming_chains: list[NamingChain] = field(default_factory=list)
    propagation_traces: list[PropagationTrace] = field(default_factory=list)
    summary: dict = field(default_factory=dict)


# --- Stage data extraction ---

def _obj_to_dict(obj: Any, fields: list[str], renames: Optional[dict] = None) -> dict:
    """Extract fields from a dataclass-like object into a dict, with optional key renames."""
    renames = renames or {}
    d: dict[str, Any] = {}
    for f in fields:
        out_key = renames.get(f, f)
        d[out_key] = getattr(obj, f, None)
    return d


def extract_stage_data(stage_name: str, output: Any) -> dict:
    """Convert typed stage output to a plain dict for diffing."""
    if stage_name == "infer":
        caps = []
        for c in getattr(output, "capabilities", []):
            d = _obj_to_dict(c, ["id", "name"])
            d["source_files"] = getattr(c, "module_sources", [])
            caps.append(d)
        return {
            "capabilities": caps,
            "actors": [_obj_to_dict(a, ["id", "name"]) for a in getattr(output, "actors", [])],
            "behaviors": [_obj_to_dict(b, ["id", "name"]) for b in getattr(output, "behaviors", [])],
        }

    if stage_name == "allocate":
        comps = []
        for c in getattr(output, "components", []):
            comps.append(_obj_to_dict(c, ["id", "name", "files", "layer", "capability_id"]))
        return {"components": comps}

    if stage_name == "relate":
        rels = []
        for r in getattr(output, "relationships", []):
            rels.append({
                "from": getattr(r, "from_id", None),
                "to": getattr(r, "to_id", None),
                "type": getattr(r, "type", None),
            })
        return {"relationships": rels}

    if stage_name == "specify":
        ifaces = []
        for i in getattr(output, "interfaces", []):
            ifaces.append(_obj_to_dict(i, ["name", "type", "component_id"]))
        return {"interfaces": ifaces}

    if stage_name == "contract":
        contracts = []
        for c in getattr(output, "contracts", []):
            contracts.append(_obj_to_dict(c, ["test_file", "component_id"]))
        return {"contracts": contracts}

    if stage_name == "validate":
        return {
            "score": getattr(output, "score", 0),
            "issues": [_obj_to_dict(i, ["id", "message", "severity"]) for i in getattr(output, "issues", [])],
        }

    # Fallback: try to serialize whatever we got
    return {"raw": str(output)}


# --- Diff engine ---

def _find_entity_lists(data: dict) -> list[tuple[str, list[dict]]]:
    """Return (key, list) pairs for all entity-list values in data."""
    return [(k, v) for k, v in data.items() if isinstance(v, list)]


def diff_stage_outputs(stage: str, det: dict, llm: dict) -> StageGap:
    """Diff deterministic vs LLM output at entity level."""
    added: list[dict] = []
    removed: list[dict] = []
    renamed: list[dict] = []

    all_keys = set(det.keys()) | set(llm.keys())
    for key in all_keys:
        det_list = det.get(key, [])
        llm_list = llm.get(key, [])
        if not isinstance(det_list, list) or not isinstance(llm_list, list):
            continue

        # Index by id
        det_by_id = {e.get("id"): e for e in det_list if isinstance(e, dict) and e.get("id")}
        llm_by_id = {e.get("id"): e for e in llm_list if isinstance(e, dict) and e.get("id")}

        matched_det_ids: set[str] = set()
        matched_llm_ids: set[str] = set()

        # Match by ID
        for eid in det_by_id:
            if eid in llm_by_id:
                matched_det_ids.add(eid)
                matched_llm_ids.add(eid)
                det_name = det_by_id[eid].get("name", "")
                llm_name = llm_by_id[eid].get("name", "")
                if det_name != llm_name:
                    sim = SequenceMatcher(None, det_name, llm_name).ratio()
                    renamed.append({"det": det_name, "llm": llm_name, "similarity": sim, "id": eid})

        # Unmatched
        for eid, e in llm_by_id.items():
            if eid not in matched_llm_ids:
                added.append(e)
        for eid, e in det_by_id.items():
            if eid not in matched_det_ids:
                removed.append(e)

    return StageGap(
        stage=stage,
        deterministic=det,
        llm_alternative=llm,
        added=added,
        removed=removed,
        renamed=renamed,
    )


# --- Naming chains ---

def build_naming_chains(det_data: dict[str, dict], llm_data: dict[str, dict]) -> list[NamingChain]:
    """Trace how source file names propagate through pipeline stages."""
    # Build capability-id → source_file and component mappings from det
    cap_source: dict[str, str] = {}  # cap_id → source_file
    cap_name: dict[str, str] = {}    # cap_id → name
    comp_by_cap: dict[str, dict] = {}  # cap_id → component dict
    comp_by_id: dict[str, dict] = {}

    infer = det_data.get("infer", {})
    for c in infer.get("capabilities", []):
        cid = c.get("id", "")
        sf = c.get("source_file") or (c.get("source_files", [None]) or [None])[0]
        if sf:
            cap_source[cid] = sf
        cap_name[cid] = c.get("name", "")

    alloc = det_data.get("allocate", {})
    for comp in alloc.get("components", []):
        cid = comp.get("capability_id", "")
        if cid:
            comp_by_cap[cid] = comp
        comp_by_id[comp.get("id", "")] = comp

    specify = det_data.get("specify", {})
    iface_by_comp: dict[str, dict] = {}
    for iface in specify.get("interfaces", []):
        comp_id = iface.get("component_id", "")
        if comp_id:
            iface_by_comp[comp_id] = iface

    # Same for LLM
    llm_cap_name: dict[str, str] = {}
    llm_comp_by_cap: dict[str, dict] = {}
    llm_iface_by_comp: dict[str, dict] = {}

    llm_infer = llm_data.get("infer", {})
    for c in llm_infer.get("capabilities", []):
        llm_cap_name[c.get("id", "")] = c.get("name", "")

    llm_alloc = llm_data.get("allocate", {})
    for comp in llm_alloc.get("components", []):
        cid = comp.get("capability_id", "")
        if cid:
            llm_comp_by_cap[cid] = comp

    llm_specify = llm_data.get("specify", {})
    for iface in llm_specify.get("interfaces", []):
        comp_id = iface.get("component_id", "")
        if comp_id:
            llm_iface_by_comp[comp_id] = iface

    chains: list[NamingChain] = []
    for cap_id, source in cap_source.items():
        stages: dict[str, str] = {}
        llm_stages: dict[str, str] = {}

        # infer stage
        if cap_id in cap_name:
            stages["infer"] = cap_name[cap_id]
        if cap_id in llm_cap_name:
            llm_stages["infer"] = llm_cap_name[cap_id]

        # allocate stage
        comp = comp_by_cap.get(cap_id)
        if comp:
            stages["allocate"] = comp.get("name", "")
            llm_comp = llm_comp_by_cap.get(cap_id)
            if llm_comp:
                llm_stages["allocate"] = llm_comp.get("name", "")
            # specify stage
            iface = iface_by_comp.get(comp.get("id", ""))
            if iface:
                stages["specify"] = iface.get("name", "")
            llm_iface = llm_iface_by_comp.get(comp.get("id", ""))
            if llm_iface:
                llm_stages["specify"] = llm_iface.get("name", "")

        generic = any(is_generic_name(n) for n in stages.values())
        chains.append(NamingChain(source=source, stages=stages, llm_stages=llm_stages, is_generic=generic))

    return chains


# --- Propagation tracing ---

def trace_propagation(det_data: dict[str, dict]) -> list[PropagationTrace]:
    """Find generic names in early stages and trace their propagation downstream."""
    traces: list[PropagationTrace] = []

    infer = det_data.get("infer", {})
    alloc = det_data.get("allocate", {})
    specify = det_data.get("specify", {})

    for cap in infer.get("capabilities", []):
        name = cap.get("name", "")
        if not is_generic_name(name):
            continue

        cap_id = cap.get("id", "")
        affected: list[dict] = []

        # Check allocate
        for comp in alloc.get("components", []):
            if comp.get("capability_id") == cap_id:
                affected.append({
                    "stage": "allocate",
                    "entity": comp.get("name", ""),
                    "effect": f"Component inherits generic name from capability '{name}'",
                })
                # Check specify
                comp_id = comp.get("id", "")
                for iface in specify.get("interfaces", []):
                    if iface.get("component_id") == comp_id:
                        affected.append({
                            "stage": "specify",
                            "entity": iface.get("name", ""),
                            "effect": f"Interface name derived from generic component '{comp.get('name', '')}'",
                        })

        if affected:
            traces.append(PropagationTrace(
                origin_stage="infer",
                origin_entity=name,
                origin_issue=f"Generic capability name '{name}'",
                affected=affected,
            ))

    return traces


# --- Orchestrator ---

async def run_gap_analysis(
    repo_path: Path,
    llm_callback: Callable,
) -> GapAnalysisResult:
    """Run full gap analysis: pipeline stages, LLM alternatives, diff, trace."""
    # This is the high-level orchestrator - tested at integration level
    # Placeholder for now; wired up when LLM integration is ready
    return GapAnalysisResult(repo_path=str(repo_path))
