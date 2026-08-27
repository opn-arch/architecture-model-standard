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
            d["source_files"] = [str(s) for s in getattr(c, "module_sources", [])]
            caps.append(d)
        return {
            "capabilities": caps,
            "actors": [_obj_to_dict(a, ["id", "name"]) for a in getattr(output, "actors", [])],
            "behaviors": [_obj_to_dict(b, ["id", "name"]) for b in getattr(output, "behaviors", [])],
        }

    if stage_name == "allocate":
        comps = []
        for c in getattr(output, "components", []):
            d = _obj_to_dict(c, ["id", "name", "layer", "capability_id"])
            d["files"] = [str(f) for f in getattr(c, "files", [])]
            comps.append(d)
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
            cap_source[cid] = str(sf)
        cap_name[cid] = c.get("name", "")

    alloc = det_data.get("allocate", {})
    for comp in alloc.get("components", []):
        cid = comp.get("capability_id", "")
        if cid:
            comp_by_cap[cid] = comp
            # If no source_file on capability, use first file from component
            if cid not in cap_source and comp.get("files"):
                cap_source[cid] = str(comp["files"][0])
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
    """Run full gap analysis: pipeline stages, LLM alternatives, diff, trace.

    1. Runs the deterministic pipeline (observe→validate)
    2. For each reviewable stage, asks LLM to re-infer from same inputs
    3. Diffs deterministic vs LLM outputs
    4. Builds naming chains and propagation traces
    """
    from .observe import ObserveStage
    from .infer import InferStage
    from .allocate import AllocateStage
    from .relate import RelateStage
    from .specify import SpecifyStage
    from .contract import ContractStage
    from .validate import ValidateStage
    from .coordinator import PipelineCoordinator
    from .protocol import PipelineContext
    from .gap_prompts import build_reinfer_prompt, parse_reinfer_response

    # Run deterministic pipeline
    stages = {
        "observe": ObserveStage(),
        "infer": InferStage(),
        "allocate": AllocateStage(),
        "relate": RelateStage(),
        "specify": SpecifyStage(),
        "contract": ContractStage(),
        "validate": ValidateStage(),
    }
    coord = PipelineCoordinator(stages)
    ctx = PipelineContext(repo_path=repo_path, output_dir=repo_path / ".architecture")

    try:
        results = coord.run_all(ctx)
    except Exception as e:
        return GapAnalysisResult(
            repo_path=str(repo_path),
            summary={"error": str(e)},
        )

    # Extract structured data from each stage's output
    reviewable = ["infer", "allocate", "relate", "specify", "contract", "validate"]
    stage_gaps: list[StageGap] = []
    det_data: dict[str, dict] = {}
    llm_data: dict[str, dict] = {}

    for stage_name in reviewable:
        if stage_name not in results:
            continue
        stage_result = results[stage_name]
        det = extract_stage_data(stage_name, stage_result.output)
        det_data[stage_name] = det

    # Extract observe data for building prompts
    observe_modules: list[dict] = []
    observe_imports: list[dict] = []
    observe_test_files: list[str] = []
    if "observe" in results:
        obs = results["observe"].output
        for m in getattr(obs, "modules", []):
            funcs = [f.name if hasattr(f, "name") else str(f) for f in getattr(m, "functions", [])]
            classes = [c.name if hasattr(c, "name") else str(c) for c in getattr(m, "classes", [])]
            observe_modules.append({"path": str(getattr(m, "path", "")), "functions": funcs, "classes": classes})
        for e in getattr(obs, "import_edges", []):
            observe_imports.append({"source": str(getattr(e, "source", "")), "target": str(getattr(e, "target", ""))})
        observe_test_files = [str(t) for t in getattr(obs, "test_files", [])]

    # For each stage, build the right INPUT context and call LLM
    for stage_name in reviewable:
        if stage_name not in det_data:
            continue
        det = det_data[stage_name]

        # Build prompt kwargs: what each stage needs as INPUT
        prompt_kwargs: dict[str, Any] = {}
        if stage_name == "infer":
            prompt_kwargs["modules"] = observe_modules
        elif stage_name == "allocate":
            prompt_kwargs["modules"] = observe_modules
            prompt_kwargs["capabilities"] = det_data.get("infer", {}).get("capabilities", [])
        elif stage_name == "relate":
            prompt_kwargs["components"] = det_data.get("allocate", {}).get("components", [])
            prompt_kwargs["capabilities"] = det_data.get("infer", {}).get("capabilities", [])
            prompt_kwargs["imports"] = observe_imports
        elif stage_name == "specify":
            prompt_kwargs["components"] = det_data.get("allocate", {}).get("components", [])
        elif stage_name == "contract":
            prompt_kwargs["components"] = det_data.get("allocate", {}).get("components", [])
            prompt_kwargs["test_files"] = observe_test_files
        elif stage_name == "validate":
            prompt_kwargs["model_summary"] = {
                "components": len(det_data.get("allocate", {}).get("components", [])),
                "capabilities": len(det_data.get("infer", {}).get("capabilities", [])),
                "relationships": len(det_data.get("relate", {}).get("relationships", [])),
            }

        prompt = build_reinfer_prompt(stage_name, **prompt_kwargs)
        try:
            response = await llm_callback(stage_name, prompt, {})
            llm = parse_reinfer_response(stage_name, response)
        except Exception:
            llm = {}
        llm_data[stage_name] = llm

        gap = diff_stage_outputs(stage_name, det, llm)
        stage_gaps.append(gap)

    chains = build_naming_chains(det_data, llm_data)
    propagation = trace_propagation(det_data)

    total_gaps = sum(len(g.added) + len(g.removed) + len(g.renamed) for g in stage_gaps)

    return GapAnalysisResult(
        repo_path=str(repo_path),
        stage_gaps=stage_gaps,
        naming_chains=chains,
        propagation_traces=propagation,
        summary={
            "stages_analyzed": len(stage_gaps),
            "total_gaps": total_gaps,
            "naming_chains": len(chains),
            "propagation_traces": len(propagation),
        },
    )
