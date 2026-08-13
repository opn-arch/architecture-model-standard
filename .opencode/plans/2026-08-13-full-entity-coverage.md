# Full Entity Coverage Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the extraction pipeline produce complete architecture models with all 7 entity types — especially behaviors (use cases + workflows), interfaces, constraints, and layers — both deterministically and via LLM enrichment.

**Architecture:** Three levels of improvement: (1) Fix pipeline wiring so existing stages (specify, contract) actually run, (2) Enhance infer stage with richer behavior/use-case inference from AST data, (3) Ensure synthesize propagates all entity types to subsystem models. LLM enrichment resolves uncertainties the deterministic pipeline flags.

**Tech Stack:** Python dataclasses, AST analysis (existing observe data), pipeline stage protocol.

---

## Current State

The pipeline has 10 stages but only 5 entity types make it into output models:

| Entity | Deterministic | In Output | Gap |
|--------|:---:|:---:|-----|
| Components | ✅ allocate | ✅ | None |
| Capabilities | ✅ infer | ✅ | Shallow (just names) |
| Behaviors | ⚠️ route-only | ❌ not serialized | Critical — no use cases, no workflows |
| Actors | ⚠️ generic | ⚠️ SoS only | Not in subsystem models |
| Interfaces | ✅ specify stage | ❌ stage not wired | specify exists but never runs |
| Constraints | ✅ observe detects | ❌ dropped | Observed then ignored |
| Layers | ⚠️ keyword path match | ❌ synthetic IDs only | No first-class entities |

Root causes:
1. `validate` and `decompose` don't depend on `specify`/`contract` → those stages never run
2. `synthesize._build_system_model_yaml()` only copies components + capabilities + relationships
3. `infer._infer_behaviors()` only extracts from HTTP routes
4. No mechanism for use-case inference from CLI commands, class hierarchies, or test scenarios

---

### Task 1: Wire specify + contract into the dependency chain

**Files:**
- Modify: `src/architecture_model/pipeline/validate.py:27` — add `specify` and `contract` to requires
- Modify: `src/architecture_model/pipeline/decompose.py:22` — add `specify` to requires  
- Test: `tests/test_pipeline_stages.py` — add test verifying specify runs before validate

**Step 1: Write the failing test**

Add to `tests/test_pipeline_stages.py`:

```python
def test_validate_depends_on_specify():
    """Validate should depend on specify so interfaces are available."""
    from architecture_model.pipeline.validate import ValidateStage
    stage = ValidateStage()
    assert "specify" in stage.requires
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_pipeline_stages.py::test_validate_depends_on_specify -v`
Expected: FAIL — "specify" not in requires

**Step 3: Update dependencies**

In `validate.py` line 27, change:
```python
requires: list[str] = ["infer", "allocate", "relate"]
```
to:
```python
requires: list[str] = ["infer", "allocate", "relate", "specify", "contract"]
```

In `decompose.py` line 22, change:
```python
requires = ["allocate", "relate"]
```
to:
```python
requires = ["allocate", "relate", "specify"]
```

**Step 4: Run tests**

Run: `pytest tests/test_pipeline_stages.py -v --tb=short`
Expected: ALL PASS

**Step 5: Commit**

```bash
git commit -m "fix(pipeline): wire specify+contract into stage dependencies"
```

---

### Task 2: Infer actor-goal use cases from routes, CLI, and public APIs

**Files:**
- Modify: `src/architecture_model/pipeline/infer.py` — enhance `_infer_behaviors()`
- Modify: `src/architecture_model/pipeline/infer_types.py` — add `behavior_type` field to `InferredBehavior`
- Test: `tests/test_pipeline_stages.py` — add behavior inference tests

**Step 1: Write the failing test**

```python
def test_infer_cli_use_cases(tmp_path):
    """CLI commands should produce use-case behaviors."""
    from architecture_model.pipeline.infer import InferStage
    from architecture_model.pipeline.observe_types import (
        Inventory, ModuleRecord, FunctionRecord,
    )
    from architecture_model.pipeline.protocol import PipelineContext, StageResult

    # Module with CLI command pattern
    mod = ModuleRecord(
        path=Path("manage.py"),
        functions=[
            FunctionRecord(name="handle", params=["self", "options"], 
                          decorators=[], calls=["migrate", "flush"],
                          docstring="Run database migrations"),
        ],
        classes=[],
        imports=["click"],
        constants=[],
        line_count=50,
        docstring="Management command for migrations",
    )
    inventory = Inventory(modules=[mod], edges=[], routes=[], constraints=[], 
                          test_files=[], docs=[])

    ctx = PipelineContext(repo_path=tmp_path)
    ctx.cache["observe"] = StageResult(
        output=inventory, quality=QualityMetrics(score=100),
        diagnostics=[], uncertainties=[], input_hash="1",
        duration_ms=0, version="1.0",
    )

    stage = InferStage()
    result = stage.run(ctx)
    behaviors = result.output.behaviors
    
    # Should have at least one CLI use case
    cli_behaviors = [b for b in behaviors if b.behavior_type == "use_case"]
    assert len(cli_behaviors) >= 1
    assert any("migration" in b.name.lower() or "manage" in b.name.lower() for b in cli_behaviors)
```

**Step 2: Add `behavior_type` to InferredBehavior**

In `infer_types.py`, add field:
```python
@dataclass
class InferredBehavior:
    id: str
    name: str
    actor_id: str = ""
    capability_id: str = ""
    steps: list[str] = field(default_factory=list)
    triggers: list[str] = field(default_factory=list)
    behavior_type: str = "use_case"  # use_case | workflow | route_handler
```

**Step 3: Enhance `_infer_behaviors()` in infer.py**

Add three new behavior sources after the existing route-based inference:

```python
def _infer_behaviors(self, inventory: Inventory, capabilities, actors, ctx: PipelineContext) -> list[InferredBehavior]:
    behaviors = []
    beh_counter = 0
    actor_id = actors[0].id if actors else ""
    
    # 1. Route-based behaviors (existing, mark as route_handler)
    for route in inventory.routes:
        beh_counter += 1
        behaviors.append(InferredBehavior(
            id=f"BEH-{beh_counter}",
            name=f"{route.method} {route.path}",
            actor_id=actor_id,
            capability_id=self._match_cap(route, capabilities),
            steps=[route.function_name],
            behavior_type="route_handler",
        ))
    
    # 2. CLI command use cases
    for mod in inventory.modules:
        has_cli = any("click" in imp or "typer" in imp or "argparse" in imp for imp in mod.imports)
        if not has_cli:
            continue
        # Find handle/main/command functions
        for func in mod.functions:
            if func.name in ("handle", "main", "run", "execute") or \
               any(d for d in func.decorators if "command" in d or "click" in d):
                beh_counter += 1
                name = mod.path.stem.replace("_", " ").title()
                desc = func.docstring or f"CLI: {mod.path.stem}"
                behaviors.append(InferredBehavior(
                    id=f"BEH-{beh_counter}",
                    name=f"CLI: {name}",
                    actor_id=actor_id,
                    steps=func.calls[:5] if func.calls else [func.name],
                    behavior_type="use_case",
                ))
    
    # 3. Public API use cases — classes with public methods that form coherent operations
    #    Detect: abstract base classes, handler classes, view classes
    for mod in inventory.modules:
        for cls in mod.classes:
            # Skip private/test classes
            if cls.name.startswith("_") or "Test" in cls.name:
                continue
            # Detect handler/view/command patterns
            is_handler = any(base for base in cls.bases if any(
                kw in base.lower() for kw in ("view", "handler", "command", "middleware", "mixin")
            ))
            if not is_handler:
                continue
            public_methods = [m for m in cls.methods if not m.startswith("_")]
            if not public_methods:
                continue
            beh_counter += 1
            behaviors.append(InferredBehavior(
                id=f"BEH-{beh_counter}",
                name=f"{cls.name}",
                actor_id=actor_id,
                steps=public_methods[:10],
                behavior_type="use_case",
            ))
    
    return behaviors
```

**Step 4: Run tests**

Run: `pytest tests/test_pipeline_stages.py -v --tb=short`
Expected: ALL PASS

**Step 5: Commit**

```bash
git commit -m "feat(infer): infer use-case behaviors from CLI commands and handler classes"
```

---

### Task 3: Infer technical workflow behaviors from class hierarchies and decorator chains

**Files:**
- Modify: `src/architecture_model/pipeline/infer.py` — add `_infer_workflows()`
- Test: `tests/test_pipeline_stages.py`

**Step 1: Write the failing test**

```python
def test_infer_middleware_workflow(tmp_path):
    """Middleware classes should produce workflow behaviors."""
    from architecture_model.pipeline.infer import InferStage
    from architecture_model.pipeline.observe_types import (
        Inventory, ModuleRecord, ClassRecord, FunctionRecord,
    )

    mod = ModuleRecord(
        path=Path("django/middleware/csrf.py"),
        functions=[],
        classes=[
            ClassRecord(
                name="CsrfViewMiddleware",
                bases=["MiddlewareMixin"],
                methods=["process_request", "process_view", "process_response"],
                method_details=[],
                attributes=[],
                decorators=[],
                is_abstract=False,
            ),
        ],
        imports=["django.utils.deprecation"],
        constants=[],
        line_count=100,
        docstring="",
    )
    inventory = Inventory(modules=[mod], edges=[], routes=[], constraints=[],
                          test_files=[], docs=[])

    ctx = PipelineContext(repo_path=tmp_path)
    ctx.cache["observe"] = StageResult(
        output=inventory, quality=QualityMetrics(score=100),
        diagnostics=[], uncertainties=[], input_hash="1",
        duration_ms=0, version="1.0",
    )

    stage = InferStage()
    result = stage.run(ctx)
    workflows = [b for b in result.output.behaviors if b.behavior_type == "workflow"]
    assert len(workflows) >= 1
    assert any("CsrfViewMiddleware" in w.name or "csrf" in w.name.lower() for w in workflows)
    # Steps should reflect the method ordering
    csrf_wf = [w for w in workflows if "csrf" in w.name.lower() or "Csrf" in w.name][0]
    assert "process_request" in csrf_wf.steps
```

**Step 2: Implement `_infer_workflows()`**

Add to `_infer_behaviors()` after the use-case section:

```python
    # 4. Workflow behaviors — ordered method chains in middleware/pipeline/handler classes
    WORKFLOW_PATTERNS = {
        "middleware": {
            "bases": ["middleware", "mixin"],
            "ordered_methods": ["process_request", "process_view", "process_response", "process_exception"],
        },
        "lifecycle": {
            "bases": ["model", "form", "serializer"],
            "ordered_methods": ["clean", "validate", "save", "delete"],
        },
        "test": {
            "bases": ["testcase", "test"],
            "ordered_methods": ["setUp", "test_*", "tearDown"],
        },
    }
    
    for mod in inventory.modules:
        for cls in mod.classes:
            if cls.name.startswith("_"):
                continue
            for pattern_name, pattern in WORKFLOW_PATTERNS.items():
                # Check if class bases match
                bases_lower = [b.lower() for b in cls.bases]
                if not any(kw in base for base in bases_lower for kw in pattern["bases"]):
                    continue
                # Find matching ordered methods
                matched_steps = []
                for method_pattern in pattern["ordered_methods"]:
                    if method_pattern.endswith("*"):
                        prefix = method_pattern[:-1]
                        matched_steps.extend(m for m in cls.methods if m.startswith(prefix))
                    elif method_pattern in cls.methods:
                        matched_steps.append(method_pattern)
                if len(matched_steps) >= 2:
                    beh_counter += 1
                    behaviors.append(InferredBehavior(
                        id=f"BEH-{beh_counter}",
                        name=f"{cls.name} {pattern_name} workflow",
                        steps=matched_steps,
                        behavior_type="workflow",
                    ))
```

**Step 3: Run tests, commit**

```bash
git commit -m "feat(infer): infer workflow behaviors from middleware/lifecycle class patterns"
```

---

### Task 4: Propagate all entity types through synthesize

**Files:**
- Modify: `src/architecture_model/pipeline/synthesize.py` — `_build_system_model_yaml()` must include behaviors, interfaces, constraints, layers, actors
- Test: `tests/test_pipeline_stages.py`

**Step 1: Write the failing test**

```python
def test_synthesize_includes_behaviors():
    """Synthesize should propagate behaviors into subsystem model YAML."""
    # Set up a minimal pipeline context with all stages cached
    # The system model YAML should contain a 'behaviors:' section
    ...
```

**Step 2: Enhance `_build_system_model_yaml()`**

Currently this method builds YAML from components + capabilities + relationships. It needs to also include:

1. **Behaviors** — filter infer result behaviors that reference components in this system
2. **Interfaces** — filter specify result interfaces by component_id
3. **Constraints** — from observe inventory, filter by source file paths in this system
4. **Layers** — create first-class layer entities from the unique `layer` values on components
5. **Actors** — from infer result, include if they reference capabilities in this system

The key change: read from `ctx.get("specify")` and `ctx.get("infer")` to get interfaces and behaviors, then filter by which components belong to the current system boundary.

```python
def _build_system_model_yaml(self, system, ctx, components, capabilities, relationships):
    # ... existing component/capability/relationship building ...
    
    # Add behaviors
    infer_result = ctx.get("infer")
    if infer_result:
        sys_cap_ids = {c.id for c in capabilities}
        behaviors = [
            b for b in infer_result.output.behaviors
            if b.capability_id in sys_cap_ids or not b.capability_id
        ]
        if behaviors:
            yaml_dict["entities"]["behaviors"] = [
                {"id": b.id, "name": b.name, "type": b.behavior_type,
                 "steps": b.steps, "actor_id": b.actor_id}
                for b in behaviors
            ]
    
    # Add interfaces
    specify_result = ctx.get("specify")
    if specify_result:
        sys_comp_ids = {c.id for c in components}
        interfaces = [
            i for i in specify_result.output.interfaces
            if i.component_id in sys_comp_ids
        ]
        if interfaces:
            yaml_dict["entities"]["interfaces"] = [
                {"id": i.id, "name": i.name, "type": i.interface_type,
                 "component_id": i.component_id, "methods": i.methods}
                for i in interfaces
            ]
    
    # Add constraints
    observe_result = ctx.get("observe")
    if observe_result:
        sys_files = {f for c in components for f in c.files}
        constraints = [
            c for c in observe_result.output.constraints
            if Path(c.source) in sys_files or not c.source
        ]
        if constraints:
            yaml_dict["entities"]["constraints"] = [
                {"id": f"CON-{i+1}", "name": c.name, "value": c.value,
                 "type": c.constraint_type, "source": c.source}
                for i, c in enumerate(constraints)
            ]
    
    # Add layers as first-class entities
    unique_layers = {c.layer for c in components if c.layer}
    if unique_layers:
        yaml_dict["entities"]["layers"] = [
            {"id": f"LAYER-{layer}", "name": layer.title()}
            for layer in sorted(unique_layers)
        ]
```

**Step 3: Run tests, commit**

```bash
git commit -m "feat(synthesize): propagate behaviors, interfaces, constraints, layers to subsystem models"
```

---

### Task 5: Add LLM uncertainty flags for deeper behavioral analysis

**Files:**
- Modify: `src/architecture_model/pipeline/infer.py` — add uncertainties for complex behaviors
- No code changes in synthesize — LLM enrichment happens via MCP resolutions between stages

**Step 1: Write the failing test**

```python
def test_infer_flags_complex_behavior_uncertainty(tmp_path):
    """Complex classes should flag uncertainties for LLM enrichment."""
    from architecture_model.pipeline.infer import InferStage
    
    # A module with a complex class that has many methods but no clear pattern
    mod = ModuleRecord(
        path=Path("django/db/models/query.py"),
        functions=[],
        classes=[ClassRecord(
            name="QuerySet",
            bases=["object"],
            methods=["filter", "exclude", "annotate", "aggregate", "values", 
                     "order_by", "distinct", "union", "intersection", "difference",
                     "select_related", "prefetch_related", "defer", "only",
                     "using", "all", "none", "get", "create", "update", "delete",
                     "count", "exists", "first", "last", "earliest", "latest"],
            method_details=[], attributes=[], decorators=[], is_abstract=False,
        )],
        imports=[], constants=[], line_count=2000, docstring="",
    )
    inventory = Inventory(modules=[mod], edges=[], routes=[], constraints=[],
                          test_files=[], docs=[])
    ctx = PipelineContext(repo_path=tmp_path)
    ctx.cache["observe"] = StageResult(
        output=inventory, quality=QualityMetrics(score=100),
        diagnostics=[], uncertainties=[], input_hash="1",
        duration_ms=0, version="1.0",
    )

    stage = InferStage()
    result = stage.run(ctx)
    
    # Should flag uncertainty for complex class needing LLM behavioral analysis
    complex_unc = [u for u in result.uncertainties 
                   if u.category == "complex_behavior"]
    assert len(complex_unc) >= 1
    assert "QuerySet" in complex_unc[0].description
```

**Step 2: Add uncertainty flagging for complex classes**

At the end of `_infer_behaviors()`, add:

```python
    # Flag complex classes for LLM behavioral enrichment
    COMPLEX_METHOD_THRESHOLD = 15
    for mod in inventory.modules:
        for cls in mod.classes:
            if cls.name.startswith("_") or "Test" in cls.name:
                continue
            public_methods = [m for m in cls.methods if not m.startswith("_")]
            if len(public_methods) >= COMPLEX_METHOD_THRESHOLD:
                uncertainties.append(Uncertainty(
                    category="complex_behavior",
                    description=f"{cls.name} in {mod.path} has {len(public_methods)} public methods — needs LLM analysis to identify key workflows and use cases",
                    context={"class": cls.name, "file": str(mod.path), 
                             "methods": public_methods[:20],
                             "method_count": len(public_methods)},
                    suggested_fallback=f"Create generic workflow for {cls.name}",
                    priority="medium",
                ))
```

Also flag modules with many interconnected functions:

```python
    # Flag modules with high function count for workflow analysis
    MODULE_FUNCTION_THRESHOLD = 10
    for mod in inventory.modules:
        public_funcs = [f for f in mod.functions if not f.name.startswith("_")]
        if len(public_funcs) >= MODULE_FUNCTION_THRESHOLD:
            # Check if functions call each other (workflow signal)
            func_names = {f.name for f in public_funcs}
            cross_calls = sum(1 for f in public_funcs 
                            for c in (f.calls or []) if c in func_names)
            if cross_calls >= 3:
                uncertainties.append(Uncertainty(
                    category="complex_behavior",
                    description=f"{mod.path} has {len(public_funcs)} public functions with {cross_calls} cross-calls — likely contains workflow patterns",
                    context={"file": str(mod.path),
                             "functions": [f.name for f in public_funcs[:15]],
                             "cross_calls": cross_calls},
                    suggested_fallback=f"Create module-level workflow for {mod.path.stem}",
                    priority="medium",
                ))
```

**Step 3: Run tests, commit**

```bash
git commit -m "feat(infer): flag complex classes/modules as uncertainties for LLM behavior enrichment"
```

---

### Task 6: Enhance constraint propagation from observe through to models

**Files:**
- Modify: `src/architecture_model/pipeline/infer.py` — pass through constraints from observe
- Modify: `src/architecture_model/pipeline/infer_types.py` — add `constraints` field to InferenceResult
- Modify: `src/architecture_model/pipeline/relate.py` — add `constrained-by` relationships

**Step 1: Write the failing test**

```python
def test_constraints_produce_relationships(tmp_path):
    """Observed constraints should produce constrained-by relationships."""
    # Setup pipeline with constraints in observe output
    # Verify relate produces constrained-by relationships
    ...
```

**Step 2: Add constraints pass-through in infer**

In `infer_types.py`:
```python
@dataclass
class InferenceResult:
    capabilities: list[InferredCapability] = field(default_factory=list)
    actors: list[InferredActor] = field(default_factory=list)
    behaviors: list[InferredBehavior] = field(default_factory=list)
    constraints: list[dict] = field(default_factory=list)  # pass-through from observe
```

In `infer.py`, at end of `run()`:
```python
# Pass through constraints from observe
constraints = [
    {"id": f"CON-{i+1}", "name": c.name, "value": c.value, 
     "type": c.constraint_type, "source": c.source}
    for i, c in enumerate(inventory.constraints)
]
result = InferenceResult(capabilities=caps, actors=actors, 
                         behaviors=behaviors, constraints=constraints)
```

In `relate.py`, add `constrained-by` relationships:
```python
# Constrained-by relationships
infer_result = ctx.get("infer")
if infer_result and hasattr(infer_result.output, 'constraints'):
    for con in infer_result.output.constraints:
        # Technology constraints apply to all components
        if con.get("type") == "TECHNOLOGY":
            for comp in allocation.components:
                relationships.append(DerivedRelationship(
                    from_id=comp.id,
                    to_id=con["id"],
                    rel_type="constrained-by",
                    evidence_source="constraint_detection",
                ))
```

**Step 3: Run tests, commit**

```bash
git commit -m "feat(pipeline): propagate constraints through infer/relate as constrained-by relationships"
```

---

### Task 7: Create first-class layer entities in relate stage

**Files:**
- Modify: `src/architecture_model/pipeline/relate.py` — emit layer entities alongside contains relationships
- Modify: `src/architecture_model/pipeline/relate_types.py` — add `layers` to RelateResult if needed

**Step 1: Check current relate_types.py structure**

Read `relate_types.py` to see if layers can be added to `RelateResult`.

**Step 2: Add layer entity emission**

Currently relate creates synthetic `LAYER-{name}` IDs in contains-relationships but no actual layer entity list. Add:

```python
# In RelateResult (relate_types.py), add:
layers: list[dict] = field(default_factory=list)

# In relate.py, after building contains relationships:
unique_layers = {comp.layer for comp in allocation.components if comp.layer}
result.layers = [
    {"id": f"LAYER-{layer}", "name": layer.title(), "description": f"Components in the {layer} architectural tier"}
    for layer in sorted(unique_layers)
]
```

**Step 3: Synthesize reads layers from relate result**

Already handled in Task 4 — synthesize builds layers from component allocations. But now it should prefer the relate result's layer entities if available.

**Step 4: Run tests, commit**

```bash
git commit -m "feat(relate): emit first-class layer entities"
```

---

### Task 8: Update architecture-extraction skill with LLM enrichment for behaviors

**Files:**
- Modify: `~/.config/opencode/skills/superpowers/architecture-extraction/SKILL.md`

**What to add:**

In the LLM enrichment section, add guidance for resolving `complex_behavior` uncertainties:

```markdown
### Resolving complex_behavior Uncertainties

When the pipeline flags `complex_behavior` uncertainties:

1. **Read the flagged file** — understand the class/module purpose
2. **Identify key workflows** — what sequences of method calls constitute meaningful operations?
3. **Create behavior resolutions** with format:
   ```json
   {
     "category": "complex_behavior",
     "resolution": "Identified 3 workflows: QuerySet.filter_chain (filter→exclude→annotate→values), QuerySet.crud (create→update→delete), QuerySet.aggregation (aggregate→count→exists)",
     "confidence": 0.8,
     "source": "llm_analysis",
     "for_stage": "infer"
   }
   ```
4. **Focus on actor-goal use cases** — what can a developer DO with this class?
5. **Focus on technical workflows** — what ordered sequences of operations does this class support?
```

**Step 1: Update skill, commit**

```bash
git commit -m "docs(skill): add LLM enrichment guidance for complex_behavior uncertainties"
```

---

### Task 9: Integration test with Django-like structure

**Files:**
- Modify: `tests/test_pipeline_stages.py` — add full-pipeline test verifying all entity types

**Step 1: Write integration test**

```python
def test_full_pipeline_produces_all_entity_types(tmp_path):
    """A complete pipeline run should produce all 7 entity types."""
    # Create a Django-like structure with:
    # - Routes (for route behaviors + interfaces)
    # - CLI imports (for CLI use cases)
    # - Middleware class (for workflow behaviors)
    # - Constraints in pyproject.toml
    # - Multiple layers (web, data, service)
    
    # Run full pipeline through synthesize
    # Verify output model contains:
    # 1. components (from allocate)
    # 2. capabilities (from infer)
    # 3. behaviors with behavior_type in (use_case, workflow, route_handler)
    # 4. interfaces (from specify — REST, CLI, library)
    # 5. constraints (from observe pass-through)
    # 6. layers (from allocate/relate)
    # 7. actors (from infer)
    # 8. relationships including constrained-by, exposes, contains
    ...
```

**Step 2: Implement test with full pipeline, commit**

```bash
git commit -m "test: integration test verifying all 7 entity types in pipeline output"
```

---

### Task 10: Re-extract Django and evaluate

**No code changes — operational task.**

1. Clear Django pipeline cache: `architect_pipeline(django_path, stage="observe", clear_cache=true)`
2. Run full pipeline stage-by-stage through emit
3. Verify subsystem models now contain behaviors, interfaces, constraints, layers
4. Compare entity counts to previous run
5. Record as a learning via `architect_learn`

Expected improvement:

| Entity | Before | After |
|--------|--------|-------|
| Behaviors | 0 in models | Use cases from CLI + views + handlers, workflows from middleware |
| Interfaces | 0 | REST (from routes), CLI, Library APIs |
| Constraints | 0 | Technology constraints (Python version, Django dep) |
| Layers | 0 | web, data, service, infra |

---

## Summary

| Task | Type | Description |
|------|------|-------------|
| 1 | Fix | Wire specify+contract into dependency chain |
| 2 | Feature | Infer use-case behaviors from CLI + handler classes |
| 3 | Feature | Infer workflow behaviors from middleware/lifecycle patterns |
| 4 | Feature | Propagate all entity types through synthesize |
| 5 | Feature | LLM uncertainty flags for complex behavioral analysis |
| 6 | Feature | Constraint propagation from observe through relate |
| 7 | Feature | First-class layer entities in relate |
| 8 | Docs | Architecture-extraction skill LLM enrichment guidance |
| 9 | Test | Integration test for all 7 entity types |
| 10 | Ops | Re-extract Django and evaluate |

Total: ~10 tasks, each 10-20 min. Tasks 1-7 are deterministic pipeline improvements. Task 5+8 enable LLM enrichment. Task 9 validates. Task 10 proves it on Django.
