"""Stage tracer: reverse-engineers which pipeline function created each entity."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DecisionStep:
    """One internal function's evaluation within a stage."""
    function_name: str
    line_ref: str
    what_it_checks: str
    result: str
    entities_created: list[dict] = field(default_factory=list)
    assessment: str = "✅ Correct"


@dataclass
class EntityProvenance:
    """How a specific entity was created."""
    entity_id: str
    entity_name: str
    entity_type: str
    created_by: str
    naming_heuristic: str = ""
    input_value: str = ""
    output_value: str = ""
    llm_alternative: str = ""


@dataclass
class StageTrace:
    """Complete trace of one stage's decision chain."""
    stage: str
    decisions: list[DecisionStep] = field(default_factory=list)
    entities: list[EntityProvenance] = field(default_factory=list)
    summary: dict = field(default_factory=dict)


_TRIGGER_KEYWORDS = {
    "websocket": "WebSocket Handlers",
    "socketio": "WebSocket Handlers",
    "channels": "WebSocket Handlers",
    "grpc": "gRPC Services",
    "grpcio": "gRPC Services",
    "proto": "gRPC Services",
    "celery": "Scheduled Tasks",
    "apscheduler": "Scheduled Tasks",
    "schedule": "Scheduled Tasks",
    "crontab": "Scheduled Tasks",
}

_INFRA_CAPS = {"Infrastructure & Deployment", "Database Migrations", "Configuration"}
_TRIGGER_CAPS = {"WebSocket Handlers", "gRPC Services", "Scheduled Tasks"}

_LAYER_KEYWORDS = {
    "web": {"api", "route", "view", "handler", "endpoint"},
    "data": {"model", "schema", "db", "repository"},
    "service": {"service", "usecase", "domain"},
}


def _find_llm_cap(cap_name: str, source_files: list, llm_data: dict) -> str:
    llm_caps = llm_data.get("capabilities", [])
    # Match by source_file
    for sf in source_files:
        sf_str = str(sf)
        for lc in llm_caps:
            if lc.get("source_file") and sf_str.endswith(lc["source_file"]):
                return lc["name"]
    # Match by stem similarity
    stem = cap_name.lower().replace(" ", "_")
    for lc in llm_caps:
        src = lc.get("source_file", "")
        if src and stem in src.lower():
            return lc["name"]
        if src and Path(src).stem.replace("_", "").lower() in stem.replace("_", "").lower():
            return lc["name"]
    return ""


def trace_infer(inventory, infer_output: dict, llm_data: dict) -> StageTrace:
    trace = StageTrace(stage="infer")
    caps = infer_output.get("capabilities", [])
    behaviors = infer_output.get("behaviors", [])

    # 1. Routes check
    route_count = len(inventory.routes) if inventory and hasattr(inventory, "routes") else 0
    trace.decisions.append(DecisionStep(
        function_name="_infer_from_routes",
        line_ref="infer.py:265",
        what_it_checks="Check inventory.routes for URL patterns",
        result=f"{route_count} routes found → {'USED' if route_count > 0 else 'SKIPPED'}",
    ))

    # 2. Triggers check
    found_triggers: set[str] = set()
    if inventory and hasattr(inventory, "modules"):
        for mod in inventory.modules:
            for imp in getattr(mod, "imports", []):
                imp_str = str(imp).lower() if not isinstance(imp, str) else imp.lower()
                for kw in _TRIGGER_KEYWORDS:
                    if kw in imp_str:
                        found_triggers.add(kw)
    trace.decisions.append(DecisionStep(
        function_name="_infer_from_triggers",
        line_ref="infer.py:300",
        what_it_checks="Scan imports for trigger keywords (websocket, grpc, celery, etc.)",
        result=f"Found: {sorted(found_triggers) if found_triggers else 'none'}",
    ))

    # 3. Domain modules — classify each capability
    domain_entities: list[dict] = []
    for cap in caps:
        name = cap.get("name", "")
        cap_id = cap.get("id", "")
        source_files = cap.get("source_files", [])
        prov = EntityProvenance(
            entity_id=cap_id, entity_name=name, entity_type="capability",
            created_by="", output_value=name,
        )
        if name.endswith(" Management"):
            prov.created_by = "_infer_from_routes"
            prov.naming_heuristic = "route_prefix.replace('_', ' ').title() + ' Management'"
        elif name.startswith("CLI "):
            prov.created_by = "_infer_from_cli"
            prov.naming_heuristic = "'CLI ' + group_name.title()"
        elif name in _TRIGGER_CAPS:
            prov.created_by = "_infer_from_triggers"
        elif name in _INFRA_CAPS:
            prov.created_by = "_infer_infrastructure_capabilities"
        else:
            prov.created_by = "_infer_from_domain_modules"
            prov.naming_heuristic = "stem.lstrip('_').replace('_', ' ').title()"
            # Find matching module
            if inventory and hasattr(inventory, "modules"):
                for mod in inventory.modules:
                    stem = mod.path.stem if hasattr(mod.path, "stem") else ""
                    transformed = stem.lstrip("_").replace("_", " ").title()
                    if transformed == name:
                        prov.input_value = stem
                        break

        prov.llm_alternative = _find_llm_cap(name, source_files, llm_data)
        trace.entities.append(prov)
        domain_entities.append({"name": name, "id": cap_id})

    trace.decisions.append(DecisionStep(
        function_name="_infer_from_domain_modules",
        line_ref="infer.py:180",
        what_it_checks="Transform non-test, non-init module stems into capabilities",
        result=f"{len(domain_entities)} capabilities created",
        entities_created=domain_entities,
    ))

    # 4. Behaviors check
    pipeline_b = len(behaviors)
    llm_b = len(llm_data.get("behaviors", []))
    assessment = "✅ Correct"
    if pipeline_b == 0 and llm_b > 0:
        assessment = "❌ Critical gap: behavior inference only checks web/CLI/handler patterns"
    trace.decisions.append(DecisionStep(
        function_name="_infer_behaviors",
        line_ref="infer.py:350",
        what_it_checks="Infer behaviors from route/CLI/handler patterns",
        result=f"Pipeline: {pipeline_b} behaviors, LLM: {llm_b} behaviors",
        assessment=assessment,
    ))

    # 5. Per-module assessment
    if inventory and hasattr(inventory, "modules"):
        for mod in inventory.modules:
            stem = mod.path.stem if hasattr(mod.path, "stem") else ""
            if stem.startswith("test_") or stem.endswith("_test") or stem == "__init__":
                continue
            pub_funcs = [f for f in getattr(mod, "functions", []) if not f.name.startswith("_")]
            classes = getattr(mod, "classes", [])
            passes = len(pub_funcs) >= 3 or len(classes) >= 2
            domain_entities.append({"name": stem, "passes_threshold": passes,
                                     "public_funcs": len(pub_funcs), "classes": len(classes)})

    trace.summary = {"pipeline_caps": len(caps), "llm_caps": len(llm_data.get("capabilities", [])),
                     "pipeline_behaviors": pipeline_b, "llm_behaviors": llm_b}
    return trace


def trace_allocate(inventory, alloc_output: dict, infer_data: dict, llm_data: dict) -> StageTrace:
    trace = StageTrace(stage="allocate")
    components = alloc_output.get("components", [])
    llm_comps = llm_data.get("components", [])

    all_infra = all(c.get("layer") == "infra" for c in components) if components else False

    for comp in components:
        comp_id = comp.get("id", "")
        name = comp.get("name", "")
        files = comp.get("files", [])
        layer = comp.get("layer", "infra")

        prov = EntityProvenance(entity_id=comp_id, entity_name=name, entity_type="component", created_by="")

        if comp.get("capability_id"):
            prov.created_by = "_seed_from_capabilities"
            prov.naming_heuristic = "cap.name.replace(' Management', '')"
        elif name == "Infrastructure":
            prov.created_by = "infra_catchall"
        else:
            prov.created_by = "_assign_by_import_affinity"

        # LLM alternative by file overlap
        best_match, best_overlap = "", 0
        comp_files = set(str(f) for f in files)
        for lc in llm_comps:
            lc_files = set(str(f) for f in lc.get("files", []))
            overlap = len(comp_files & lc_files)
            if overlap > best_overlap:
                best_overlap = overlap
                best_match = lc.get("name", "")
        prov.llm_alternative = best_match
        trace.entities.append(prov)

    # Layer assessment
    expected_layers: dict[str, str] = {}
    for comp in components:
        for f in comp.get("files", []):
            f_lower = str(f).lower()
            for layer_name, keywords in _LAYER_KEYWORDS.items():
                if any(kw in f_lower for kw in keywords):
                    expected_layers[comp.get("id", "")] = layer_name

    assessment = "✅ Correct"
    if all_infra and len(components) > 1:
        assessment = "⚠️ All components assigned to infra layer"

    trace.decisions.append(DecisionStep(
        function_name="layer_assignment",
        line_ref="allocate.py:120",
        what_it_checks="Assign layers based on file path keywords",
        result=f"{len(components)} components, {len(expected_layers)} with keyword-suggested layers",
        assessment=assessment,
    ))

    trace.summary = {"pipeline_components": len(components), "llm_components": len(llm_comps), "all_infra": all_infra}
    return trace


def trace_relate(inventory, relate_output: dict, alloc_data: dict, infer_data: dict, llm_data: dict) -> StageTrace:
    trace = StageTrace(stage="relate")
    rels = relate_output.get("relationships", [])

    for rel in rels:
        frm = rel.get("from", "")
        to = rel.get("to", "")
        rtype = rel.get("type", "")

        if frm.startswith("COMP") and to.startswith("CAP"):
            created_by = "realizes_derivation"
        elif frm.startswith("LAYER"):
            created_by = "layer_grouping"
        elif frm.startswith("COMP") and to.startswith("COMP"):
            created_by = "import_edge_analysis"
        elif frm.startswith("COMP") and to.startswith("IF"):
            created_by = "route_exposure"
        else:
            created_by = "unknown"

        trace.entities.append(EntityProvenance(
            entity_id=f"{frm}->{to}", entity_name=f"{frm} {rtype} {to}",
            entity_type="relationship", created_by=created_by,
        ))

    trace.summary = {"total_relationships": len(rels)}
    return trace


def trace_specify(inventory, specify_output: dict, alloc_data: dict, llm_data: dict) -> StageTrace:
    trace = StageTrace(stage="specify")
    interfaces = specify_output.get("interfaces", [])
    llm_ifs = llm_data.get("interfaces", [])

    for iface in interfaces:
        name = iface.get("name", "")
        comp_id = iface.get("component_id", "")

        if name.endswith("REST API"):
            created_by = "rest_pattern"
            nh = ""
        elif name.endswith("CLI"):
            created_by = "cli_pattern"
            nh = ""
        elif name.endswith("Library API"):
            created_by = "library_api_fallback"
            nh = 'f"{comp_id} Library API"'
        else:
            created_by = "unknown"
            nh = ""

        prov = EntityProvenance(
            entity_id=comp_id, entity_name=name, entity_type="interface",
            created_by=created_by,
            naming_heuristic=nh,
        )

        # LLM alternative by component_id
        for li in llm_ifs:
            if li.get("component_id") == comp_id:
                prov.llm_alternative = li.get("name", "")
                break
        trace.entities.append(prov)

    trace.summary = {"pipeline_interfaces": len(interfaces), "llm_interfaces": len(llm_ifs)}
    return trace


def trace_contract(inventory, contract_output: dict, alloc_data: dict, llm_data: dict) -> StageTrace:
    trace = StageTrace(stage="contract")
    contracts = contract_output.get("contracts", [])
    matched = sum(1 for c in contracts if c.get("component_id"))
    unmatched = len(contracts) - matched

    trace.decisions.append(DecisionStep(
        function_name="contract_matching",
        line_ref="contract.py:50",
        what_it_checks="Match test contracts to components by file path",
        result=f"{matched} matched, {unmatched} unmatched out of {len(contracts)}",
        assessment="✅ Correct" if unmatched == 0 else f"⚠️ {unmatched} unmatched contracts",
    ))
    trace.summary = {"matched": matched, "unmatched": unmatched, "total": len(contracts)}
    return trace


def trace_validate(validate_output: dict, llm_data: dict) -> StageTrace:
    trace = StageTrace(stage="validate")
    score = validate_output.get("score", 0)
    issues = validate_output.get("issues", [])

    trace.decisions.append(DecisionStep(
        function_name="validate_model",
        line_ref="validate.py:30",
        what_it_checks="Structural validation of the architecture model",
        result=f"Score: {score}/100, {len(issues)} issues",
        assessment="✅ Correct" if score >= 80 else f"⚠️ Low score: {score}",
    ))
    trace.summary = {"score": score, "issues": len(issues)}
    return trace


def trace_stage(stage_name: str, inventory, stage_output: dict, prior_data: dict, llm_data: dict) -> StageTrace:
    """Dispatcher that calls the right trace_* function."""
    if not stage_output:
        stage_output = {}
    if not prior_data:
        prior_data = {}
    if not llm_data:
        llm_data = {}

    if stage_name == "infer":
        return trace_infer(inventory, stage_output, llm_data)
    elif stage_name == "allocate":
        infer_data = prior_data.get("infer", {})
        return trace_allocate(inventory, stage_output, infer_data, llm_data)
    elif stage_name == "relate":
        alloc_data = prior_data.get("allocate", {})
        infer_data = prior_data.get("infer", {})
        return trace_relate(inventory, stage_output, alloc_data, infer_data, llm_data)
    elif stage_name == "specify":
        alloc_data = prior_data.get("allocate", {})
        return trace_specify(inventory, stage_output, alloc_data, llm_data)
    elif stage_name == "contract":
        alloc_data = prior_data.get("allocate", {})
        return trace_contract(inventory, stage_output, alloc_data, llm_data)
    elif stage_name == "validate":
        return trace_validate(stage_output, llm_data)
    else:
        return StageTrace(stage=stage_name)
