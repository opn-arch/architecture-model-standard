# Phase 4: LLM Write-Back + Endpoint Promotion + Federated (M3) — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close the three open loops in the substrate: (1) LLM authoring moves from view time to authoring time via write-back projectors emitting AI Proposals; (2) CLI subcommands, HTTP routes, and plugin hooks are promoted into first-class `Interface` entities so reference docs project deterministically from the model; (3) the federated (M3) parent/child model composition is completed, with cross-repo triggers wired end-to-end.

**Architecture:**
- **Write-back projectors:** new base class `WriteBackProjector` whose `project()` calls an `LLMProvider` (via the policy layer, already in `opencode_arch/llm/`) with the deterministic base view + prompt, receives structured output, packages it as an `architecture_model.ai.Proposal`, and returns a `ProjectedView` whose `diagram_spec` carries the proposal payload. `.llm` variants register alongside deterministic siblings. Applying the proposal (via existing `architect_proposal_apply`) writes semantic fields to the model — after which deterministic projectors take over.
- **Endpoint→Interface promotion:** an extractor stage (post-`observe`, pre-`allocate`) walks Python source for Click/argparse decorators, FastAPI/Flask/starlette route decorators, and setuptools entry points, and emits `Interface` entities of new sub-kinds (`cli_command`, `http_route`, `plugin_hook`). Ownership relationships (`exposes`) are created automatically. Reference docs (`family6.cli_reference`, `family6.api_reference`, `family6.plugin_guide`) become deterministic projections of the model.
- **Federated (M3) completion:** finish the `federated` slice scope path in the materializer (currently raises `NotImplementedError`), implement `resolve_ref` to load a child repo's package, extend `package_diff._diff_children` end-to-end, and add a `child_publish → parent_invalidate` trigger via webhook + filesystem watch templates.

**Tech Stack:** Python 3.11+, pytest, existing lifecycle primitives (Phase 1–3), `architecture_model.ai.{Proposal, apply_model_patch, WorkOrder}`, `opencode_arch.llm.{provider, registry, policy}`, stdlib `ast` for endpoint extraction, hashable proposal identity.

**Repos affected:**
- `architecture-model-standard` (ams) — WriteBackProjector base, endpoint extractor stage, federated materializer completion, invalidation extensions
- `opencode-arch` (oca) — LLM policy per-projector rules, MCP `architect_propose` write-back trigger, cross-repo trigger scripts

**Depends on:**
- Phase 1 merged (registry, invalidation, per-subsystem loop, freshness)
- Phase 2 merged (semantic fields, supplementary_refs, overlays, feedback journals)
- Phase 3 merged (entity-scoped slicing, entity_page projectors)

**Related skills:**
- @superpowers:test-driven-development for every task
- @superpowers:verification-before-completion before each commit
- @superpowers:subagent-driven-development for execution mode
- @superpowers:systematic-debugging when LLM outputs surface unexpected failures

**Baselines to preserve:**
- ams — post-Phase-3 baseline
- oca — post-Phase-3 baseline

**Branching:**
- ams: `feat/model-view-mapping-phase-4` off `main` (after Phase 3 merge)
- oca: `feat/model-view-mapping-phase-4` off `main` (after Phase 3 merge)

**Guardrails (rigid):**
- Never `git add -A`; stage each file explicitly.
- Never touch `.architecture*` telemetry directories.
- Never `pip install -e`; use PYTHONPATH pattern.
- One commit per task; Conventional Commit format.
- Verify test baseline before AND after each commit.
- **LLM invocations in tests are mocked.** No real network calls. Real LLM calls only via integration tests marked `@pytest.mark.integration` and gated behind an env var (`AMS_RUN_LLM_INTEGRATION=1`), off by default.
- **Determinism carve-out:** write-back projectors are non-deterministic by construction. Determinism guards apply to the *deterministic* projector for the same view; the `.llm` variant is guarded by a *proposal-validity* test (well-formed Proposal, correct WorkOrder linkage) rather than byte-equality.

---

## Task Sequence Overview

| # | Task | Repo | Behavior change? |
|---|---|:-:|:-:|
| 1 | `WriteBackProjector` base class — protocol + provider hookup | ams | Additive |
| 2 | Proposal packaging helper — `pack_proposal(view_spec, llm_output, provenance)` | ams | Additive |
| 3 | `family1.mission.llm` write-back projector (intent + goals authoring) | ams | Additive |
| 4 | `family3.component_spec.llm` write-back (dependencies_rationale + trade_offs) | ams | Additive |
| 5 | `family7.risk.llm` write-back (failure_modes + assumptions) | ams | Additive |
| 6 | `family4.use_cases.llm` write-back (behavior narratives → Behavior entities) | ams | Additive |
| 7 | LLM-variant registry naming enforcement (Phase-1 registry gets a `is_llm(name)` helper + guards) | ams | Additive |
| 8 | Endpoint extractor stage: Click/argparse detection | ams | Additive |
| 9 | Endpoint extractor stage: FastAPI/Flask/starlette route detection | ams | Additive |
| 10 | Endpoint extractor stage: setuptools entry_points detection | ams | Additive |
| 11 | Interface sub-kinds: `cli_command`, `http_route`, `plugin_hook` in schema + validator | ams | Additive |
| 12 | `family6.cli_reference` projector (from promoted Interface entities) | ams | Additive |
| 13 | `family6.api_reference` projector | ams | Additive |
| 14 | `family6.plugin_guide` projector | ams | Additive |
| 15 | Federated materializer completion: implement `resolve_ref` for local file+repo refs | ams | Additive |
| 16 | Federated slice materialization (removes NotImplementedError) | ams | Additive |
| 17 | Federated diff — end-to-end `_diff_children` walking | ams | Additive |
| 18 | Federated invalidation rules | ams | Additive |
| 19 | LLM policy per-projector budget rules | oca | Additive |
| 20 | MCP: `architect_propose` — invoke write-back projector, return Proposal | oca | Additive |
| 21 | MCP: mock provider registered for tests | oca | Additive (test infra) |
| 22 | Cross-repo trigger template: filesystem watcher (monorepo case) | oca | Additive (opt-in) |
| 23 | Cross-repo trigger template: webhook receiver (multi-repo case) | oca | Additive (opt-in) |
| 24 | `architect_docs` DEFAULT_SPECS gains `family6.cli_reference` / `api_reference` / `plugin_guide` | oca | Additive |
| 25 | CONTEXT.md refresh — ams (write-back, endpoints, M3) | ams | Docs |
| 26 | CONTEXT.md refresh — oca (propose tool, triggers, LLM policy) | oca | Docs |
| 27 | Full-suite verification pass — both repos | both | Verification |

---

## Task 1 — `WriteBackProjector` base class

**Files:**
- Create: `src/architecture_model/lifecycle/projectors/write_back.py`
- Test: `tests/lifecycle/projectors/test_write_back_base.py`

**Contract:**

```python
class WriteBackProjector(Projector):
    """Base for LLM-authoring projectors.

    Contract:
      1. Compute a deterministic base view (delegates to the sibling
         deterministic projector via `base_projector_name` class attr).
      2. Build a prompt via `build_prompt(base_view, mslice, spec)`.
      3. Invoke LLMProvider (provided by DI, never imported directly at
         module level so tests can inject a mock).
      4. Parse LLM output into a `ai.Proposal`.
      5. Return ProjectedView with:
          - diagram_spec = {"proposal": proposal.to_dict(),
                            "base_view_id": base_view.id}
          - content_kind = "ai_proposal"
    """

    base_projector_name: ClassVar[str]

    def __init__(self, provider: LLMProvider, task_class: str):
        self.provider = provider
        self.task_class = task_class

    def project(self, mslice: MaterializedSlice, spec: ViewSpec) -> ProjectedView:
        base = _dispatch(self.base_projector_name, mslice, spec)
        prompt = self.build_prompt(base, mslice, spec)
        raw = self.provider.structured(prompt, task_class=self.task_class,
                                       schema=self.expected_proposal_schema())
        proposal = self.pack_proposal(raw, mslice, spec)
        return ProjectedView(
            id=f"{spec.id}.llm",
            slice_ref=spec.slice_ref,
            projector=spec.projector,
            diagram_spec={"proposal": proposal.to_dict(),
                          "base_view_id": base.id},
            content_kind="ai_proposal",
            scope_chain=base.scope_chain,
            parent=base.parent,
            peers=base.peers,
            roll_up=base.roll_up,
        )

    def build_prompt(self, base, mslice, spec) -> str: raise NotImplementedError
    def expected_proposal_schema(self) -> dict: raise NotImplementedError
    def pack_proposal(self, raw, mslice, spec) -> Proposal: ...   # default via Task 2
```

**Test:**

```python
class _MockProvider:
    def __init__(self, canned):
        self.canned = canned
        self.calls = []
    def structured(self, prompt, task_class, schema):
        self.calls.append((prompt, task_class))
        return self.canned


def test_write_back_projector_returns_proposal_view(sample_mslice):
    class F1Test(WriteBackProjector):
        base_projector_name = "family1.mission"
        def build_prompt(self, b, m, s): return "prompt"
        def expected_proposal_schema(self): return {"type": "object"}
        def pack_proposal(self, raw, m, s):
            return Proposal(kind="patch", patch=[...],
                            provenance=Provenance(work_order_id="wo-1", ...))

    provider = _MockProvider(canned={"patches": [...]})
    p = F1Test(provider=provider, task_class="mission_authoring")
    spec = ViewSpec(id="v1", projector="family1.mission.llm",
                    slice_ref=SliceRef(...), output_content_kind="ai_proposal")
    view = p.project(sample_mslice, spec)
    assert view.content_kind == "ai_proposal"
    assert "proposal" in view.diagram_spec
    assert len(provider.calls) == 1
```

**Commit:**

```bash
git add tests/lifecycle/projectors/test_write_back_base.py \
        src/architecture_model/lifecycle/projectors/write_back.py
git commit -m "feat(projectors): add WriteBackProjector base class for .llm variants"
```

---

## Task 2 — Proposal packaging helper

**Files:**
- Create: `src/architecture_model/lifecycle/projectors/proposal_packaging.py`
- Test: `tests/lifecycle/projectors/test_proposal_packaging.py`

**Contract:**

```python
def pack_semantic_field_proposal(
    entity_id: str,
    field_name: str,
    field_value: Any,
    view_spec: ViewSpec,
    provider_name: str,
    model: str,
) -> Proposal:
    """Package a single-field semantic write into a Proposal via replace patch op."""
    return Proposal(
        kind="patch",
        patch=[{
            "op": "replace",
            "path": f"/entities/components/{entity_id}/{field_name}",
            "value": field_value,
        }],
        provenance=Provenance(
            work_order_id=f"wb:{view_spec.id}",
            prompt_digest=_compute_digest(...),
            model=model,
            provider=provider_name,
        ),
    )
```

Deterministic `Provenance.proposal_id` (SHA-256 of canonical fields) supports dedup for the same entity+field+value.

**Commit:**

```bash
git add tests/lifecycle/projectors/test_proposal_packaging.py \
        src/architecture_model/lifecycle/projectors/proposal_packaging.py
git commit -m "feat(projectors): add pack_semantic_field_proposal helper"
```

---

## Tasks 3–6 — Concrete write-back projectors

Each task follows the pattern: subclass `WriteBackProjector`, set `base_projector_name`, implement `build_prompt` (uses `doc_prompts.DOC_PROMPTS` templates where applicable), implement `expected_proposal_schema` (JSON Schema for what LLM must return), register the projector in `DEFAULT_REGISTRY` under `familyN.<name>.llm`.

**Test pattern (each task):** with mock provider returning canned JSON, projector produces a valid Proposal targeting expected fields on expected entities.

### Task 3 — `family1.mission.llm`

Authors `intent` + `goals` on Actors, top-level Capabilities, root scope.

**Prompt template stub:**
```
Given this deterministic base view of the system mission (JSON below),
propose values for each entity's `intent` (one sentence, why it exists)
and `goals` (measurable outcomes).

Return JSON of shape:
  {"authored": [{"entity_id": "...", "intent": "...", "goals": ["..."]}, ...]}
```

**Commit:** `feat(projectors): add family1.mission.llm write-back (intent + goals)`

### Task 4 — `family3.component_spec.llm`

Authors `dependencies_rationale` + `trade_offs` on Components.

**Commit:** `feat(projectors): add family3.component_spec.llm write-back (rationale + trade-offs)`

### Task 5 — `family7.risk.llm`

Authors `failure_modes` + `assumptions` on Components, Behaviors, Interfaces.

**Commit:** `feat(projectors): add family7.risk.llm write-back (FMEA + assumptions)`

### Task 6 — `family4.use_cases.llm`

Authors new Behavior entities (not just fields — a proposal that adds Behavior entities to the model based on gaps identified in use-case coverage). Uses `Proposal(kind="patch", patch=[{"op": "add", ...}])`.

**Commit:** `feat(projectors): add family4.use_cases.llm write-back (behavior authoring)`

---

## Task 7 — Registry naming enforcement for `.llm` variants

**Files:**
- Modify: `src/architecture_model/lifecycle/view_projection.py`
- Test: `tests/lifecycle/test_llm_variant_naming.py`

**Behavior:**
- `is_llm_projector(name: str) -> bool` returns `name.endswith(".llm")`.
- Registry rejects any `.llm` name unless a deterministic sibling with the same prefix is already registered (fail-loud at register time).
- `list_names(family: int, llm: bool | None = None)` filters by variant.

**Test:**

```python
def test_llm_variant_requires_deterministic_sibling():
    reg = ProjectorRegistry()
    with pytest.raises(ValueError, match="requires deterministic sibling"):
        reg.register("family1.mission.llm", _stub_projector)


def test_llm_variant_registers_when_sibling_present():
    reg = ProjectorRegistry()
    reg.register("family1.mission", _stub_projector)
    reg.register("family1.mission.llm", _stub_projector)  # no raise


def test_list_names_filters_by_variant():
    reg = ProjectorRegistry()
    reg.register("family1.mission", _stub); reg.register("family1.mission.llm", _stub)
    assert reg.list_names(family=1, llm=False) == ["family1.mission"]
    assert reg.list_names(family=1, llm=True) == ["family1.mission.llm"]
```

**Commit:**

```bash
git add tests/lifecycle/test_llm_variant_naming.py src/architecture_model/lifecycle/view_projection.py
git commit -m "feat(registry): enforce .llm variants require deterministic sibling"
```

---

## Task 8 — Endpoint extractor: Click/argparse

**Rationale:** Every CLI subcommand should surface as an Interface. Extract from Click decorators (`@click.command`, `@click.group`, `@<group>.command`) and argparse (`ArgumentParser.add_subparsers().add_parser("name")`). Include arg specs (name, type, required, default).

**Files:**
- Create: `src/architecture_model/pipeline/endpoint_extract.py`
- Create: `src/architecture_model/pipeline/endpoint_types.py`
- Test: `tests/pipeline/test_endpoint_extract_cli.py`

**Contract:**

```python
@dataclass(frozen=True)
class Endpoint:
    kind: Literal["cli_command", "http_route", "plugin_hook"]
    name: str
    file: str
    lineno: int
    args: tuple[EndpointArg, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)

def extract_cli_endpoints(source_files: Iterable[Path]) -> list[Endpoint]:
    """AST-scan for Click/argparse patterns. Deterministic: sorted by (file, lineno)."""
```

**Test:** fixture Python file with a Click group + 2 subcommands + 1 argparse subparser → asserted-count endpoints extracted with correct names + args.

**Commit:**

```bash
git add tests/pipeline/test_endpoint_extract_cli.py \
        src/architecture_model/pipeline/endpoint_extract.py \
        src/architecture_model/pipeline/endpoint_types.py
git commit -m "feat(pipeline): extract CLI endpoints (Click + argparse) via AST"
```

---

## Task 9 — Endpoint extractor: HTTP routes

**Files:**
- Modify: `src/architecture_model/pipeline/endpoint_extract.py`
- Test: `tests/pipeline/test_endpoint_extract_http.py`

**Behavior:** detect `@app.get/post/put/delete/patch`, `@router.<method>`, `@app.route`, and starlette `Route(...)`. Extract path, methods, path params.

**Commit:**

```bash
git add tests/pipeline/test_endpoint_extract_http.py src/architecture_model/pipeline/endpoint_extract.py
git commit -m "feat(pipeline): extract HTTP route endpoints (FastAPI/Flask/starlette)"
```

---

## Task 10 — Endpoint extractor: plugin hooks

**Files:**
- Modify: `src/architecture_model/pipeline/endpoint_extract.py`
- Test: `tests/pipeline/test_endpoint_extract_plugins.py`

**Behavior:** parse `pyproject.toml` `[project.entry-points]` tables + setuptools `entry_points={...}` calls in setup.py. Emit `plugin_hook` endpoints with group + name + target module:function.

**Commit:**

```bash
git add tests/pipeline/test_endpoint_extract_plugins.py src/architecture_model/pipeline/endpoint_extract.py
git commit -m "feat(pipeline): extract plugin-hook endpoints from entry_points"
```

---

## Task 11 — Interface sub-kinds in schema + validator

**Files:**
- Modify: `src/architecture_model/spec/architecture-model.schema.json`
- Modify: `src/architecture_model/core/validator.py`
- Test: `tests/spec/test_interface_subkinds.py`

**Behavior:** Interface entity gains `subkind ∈ {api, cli_command, http_route, plugin_hook, event, data, message, ...}` (existing values preserved). Validator warns when `cli_command` interface has no `metadata.args` (should be populated by extractor).

**Commit:**

```bash
git add tests/spec/test_interface_subkinds.py \
        src/architecture_model/spec/architecture-model.schema.json \
        src/architecture_model/core/validator.py
git commit -m "feat(schema): add Interface.subkind for cli_command/http_route/plugin_hook"
```

---

## Task 12 — Wire endpoint extractor into pipeline

**Files:**
- Modify: `src/architecture_model/pipeline/observe.py` (or a new stage between observe and infer)
- Test: `tests/pipeline/test_endpoint_promotion_end_to_end.py`

**Behavior:** after `observe` completes, run `endpoint_extract` over discovered Python + config files, and emit `Interface` entities with appropriate subkind. `exposes` relationships auto-created from the file's owning component (via `component.files` lookup). Rerunnable and idempotent (existing extracted Interfaces updated in place, not duplicated).

**Test:** small fixture repo with 1 Click CLI + 1 FastAPI app → after pipeline runs, model contains 3 CLI + 2 HTTP + 1 plugin_hook Interfaces with correct `exposes` edges.

**Commit:**

```bash
git add tests/pipeline/test_endpoint_promotion_end_to_end.py src/architecture_model/pipeline/observe.py
git commit -m "feat(pipeline): promote extracted endpoints to Interface entities"
```

---

## Tasks 13–15 — Reference-doc projectors

Each: register in Phase-1 registry, produce a deterministic diagram_spec sourced from Interface entities of the given subkind, integrate manifest_fragment when present for signature enrichment.

### Task 13 — `family6.cli_reference`

Groups by top-level CLI group; lists subcommands, args (from `metadata.args`), descriptions (from `intent`). Determinism guard included.

**Commit:** `feat(projectors): add family6.cli_reference (deterministic from Interface entities)`

### Task 14 — `family6.api_reference`

Groups by HTTP verb + path prefix; lists routes, path params, request/response schemas from manifest_fragment.

**Commit:** `feat(projectors): add family6.api_reference (deterministic from Interface entities)`

### Task 15 — `family6.plugin_guide`

Groups by entry-point group; lists hooks + target module + signature.

**Commit:** `feat(projectors): add family6.plugin_guide (deterministic from Interface entities)`

---

## Task 16 — Federated materializer: `resolve_ref` for local file/repo refs

**Files:**
- Modify: `src/architecture_model/lifecycle/model_slice_materializer.py`
- Test: `tests/lifecycle/test_federated_resolve_ref.py`

**Behavior:** `resolve_ref(ref: str) -> ArchitecturePackage` supports two forms:
- `file://<path>/package.yaml` — loads the child package from a local path
- `repo://<name>` — loads via a project-declared repo registry (`.architecture/repos.yaml` mapping name → path)

**Test:**

```python
def test_resolve_ref_file_form(tmp_child_repo):
    ref = f"file://{tmp_child_repo}/.architecture/lifecycle/package.yaml"
    pkg = resolve_ref(ref)
    assert pkg.id


def test_resolve_ref_repo_form(tmp_parent_repo_with_repos_yaml):
    ref = "repo://data-service"
    pkg = resolve_ref(ref)
    assert pkg.id
```

**Commit:**

```bash
git add tests/lifecycle/test_federated_resolve_ref.py src/architecture_model/lifecycle/model_slice_materializer.py
git commit -m "feat(materializer): implement resolve_ref for file:// and repo:// federated refs"
```

---

## Task 17 — Federated slice materialization

**Files:**
- Modify: `src/architecture_model/lifecycle/model_slice_materializer.py` — remove the `NotImplementedError` at line ~170
- Test: `tests/lifecycle/test_federated_materialize.py`

**Behavior:** when `slice.scope == "federated"`, materializer walks parent package's `children:` refs (via `resolve_ref`), loads each, merges entity fragments (namespaced by child `architecture_id`), and returns a single `MaterializedSlice` with a `federated_children: tuple[str, ...]` field on the fragment. Namespacing rule: entity IDs prefixed with `<child_arch_id>:` to avoid collisions.

**Test:**

```python
def test_federated_slice_materializes_across_children(tmp_parent_with_two_children):
    slice_ = ModelSlice(..., scope="federated")
    mslice = materialize(slice_, load_root_model(tmp_parent_with_two_children))
    child_ids = {e.id.split(":")[0] for e in mslice.fragment.components if ":" in e.id}
    assert child_ids == {"child-a", "child-b"}


def test_federated_materialize_deterministic(tmp_parent_with_two_children):
    slice_ = ModelSlice(..., scope="federated")
    m1 = materialize(slice_, load_root_model(tmp_parent_with_two_children))
    m2 = materialize(slice_, load_root_model(tmp_parent_with_two_children))
    assert m1.fragment.to_dict() == m2.fragment.to_dict()
```

**Commit:**

```bash
git add tests/lifecycle/test_federated_materialize.py src/architecture_model/lifecycle/model_slice_materializer.py
git commit -m "feat(materializer): complete federated slice materialization"
```

---

## Task 18 — Federated diff end-to-end

**Files:**
- Modify: `src/architecture_model/lifecycle/diff.py` (`_diff_children` currently partial)
- Test: `tests/lifecycle/test_federated_diff.py`

**Behavior:** given two parent packages that differ in child refs (added child, removed child, or child revision bump), `package_diff` returns `SemanticDiff.children: [{kind: "added"|"removed"|"revised", child_arch_id, from_rev?, to_rev?}]`.

**Commit:**

```bash
git add tests/lifecycle/test_federated_diff.py src/architecture_model/lifecycle/diff.py
git commit -m "feat(diff): complete _diff_children for federated packages"
```

---

## Task 19 — Federated invalidation rules

**Files:**
- Modify: `src/architecture_model/lifecycle/invalidation.py`
- Test: `tests/lifecycle/test_federated_invalidation.py`

**Behavior:**
- Child revision change → invalidate parent's federated views + any parent view referencing the child by federated entity ID.
- Child added → invalidate parent M1 root views (F1 mission, F3 structural).
- Child removed → invalidate all parent views that referenced the removed child's entities.

**Commit:**

```bash
git add tests/lifecycle/test_federated_invalidation.py src/architecture_model/lifecycle/invalidation.py
git commit -m "feat(invalidation): map federated diffs to parent view stale-set"
```

---

## Task 20 — LLM policy per-projector budget rules

**Files:**
- Modify: `src/opencode_arch/llm/policy.py`
- Test: `tests/llm/test_policy_per_projector.py`

**Behavior:** `.architecture/llm/policy.yaml` gains `projector_rules` map:

```yaml
projector_rules:
  family1.mission.llm:
    task_class: MissionAuthoring
    max_cost_usd_per_call: 0.50
  family7.risk.llm:
    task_class: RiskAuthoring
    max_cost_usd_per_call: 1.00
  default:
    task_class: GenericAuthoring
    max_cost_usd_per_call: 0.25
```

`OpencodeRunner.run_via_policy` accepts a `projector_name` kwarg; when present, applies the per-projector rule first, falls back to `task_class`-level rule.

**Commit:**

```bash
git add tests/llm/test_policy_per_projector.py src/opencode_arch/llm/policy.py
git commit -m "feat(llm): per-projector budget rules in policy.yaml"
```

---

## Task 21 — MCP `architect_propose` tool

**Files:**
- Create: `src/opencode_arch/mcp/tools/propose.py`
- Test: `tests/mcp/tools/test_architect_propose.py`

**Contract:**

```python
def architect_propose(
    repo_path: str,
    projector_name: str,       # must end with .llm
    slice_spec: dict,
) -> dict:
    """Invoke a write-back projector; return a Proposal envelope."""
    # 1. Validate projector_name ends with .llm and exists in registry.
    # 2. Materialize slice.
    # 3. Load provider from policy for this projector.
    # 4. Project → view.diagram_spec["proposal"].
    # 5. Persist under .architecture/ai/proposals/<proposal_id>.yaml.
    # 6. Return {ok: True, proposal_id, work_order_id, apply_hint: "architect_proposal_apply ..."}
```

**Test:** with mock provider, invoke `architect_propose` with `family1.mission.llm`, assert proposal file written, envelope has correct shape.

**Commit:**

```bash
git add tests/mcp/tools/test_architect_propose.py src/opencode_arch/mcp/tools/propose.py
git commit -m "feat(mcp): add architect_propose tool for write-back projectors"
```

---

## Task 22 — Test-only mock provider registration

**Files:**
- Create: `src/opencode_arch/llm/providers/mock.py`
- Test: `tests/llm/test_mock_provider.py`

**Contract:** `MockProvider(responses: dict[str, Any])` matches prompts by hash and returns canned responses; raises if a prompt hash is not registered. Used across all Phase-4 tests that touch `.llm` projectors.

**Commit:**

```bash
git add tests/llm/test_mock_provider.py src/opencode_arch/llm/providers/mock.py
git commit -m "test(llm): add MockProvider for write-back projector tests"
```

---

## Task 23 — Cross-repo trigger: filesystem watcher template

**Rationale:** Monorepo case — child subdirectory publishes → parent watcher script detects → parent invalidation runs.

**Files:**
- Create: `docs/templates/child-publish-watcher.sh`
- Test: `tests/templates/test_watcher_template_syntax.py`

**Behavior:** shell template using `fswatch` (or `inotifywait` on Linux) to watch `<child_repo>/.architecture/lifecycle/CURRENT` for changes, then invokes `opencode-arch invalidate --federated-child <child_arch_id>` in the parent.

**Commit:**

```bash
git add tests/templates/test_watcher_template_syntax.py docs/templates/child-publish-watcher.sh
git commit -m "feat(templates): add child-publish filesystem watcher for federated"
```

---

## Task 24 — Cross-repo trigger: webhook receiver template

**Files:**
- Create: `docs/templates/child-publish-webhook.yml` (GitHub Actions workflow)
- Test: `tests/templates/test_webhook_template_syntax.py`

**Behavior:** GH Actions workflow triggered on child repo `push` to main, calls parent repo's `repository_dispatch` event with the new child revision.

**Commit:**

```bash
git add tests/templates/test_webhook_template_syntax.py docs/templates/child-publish-webhook.yml
git commit -m "feat(templates): add webhook trigger for cross-repo federated publish"
```

---

## Task 25 — `architect_docs` DEFAULT_SPECS gains reference-doc specs

**Files:**
- Modify: `src/opencode_arch/mcp/tools/docs_specs.py`
- Test: `tests/mcp/tools/test_docs_specs_reference.py`

**Behavior:** `architect_docs(formats="cli_reference")`, `formats="api_reference"`, `formats="plugin_guide"` rebuild via `family6.*` projectors + markdown renderer.

**Commit:**

```bash
git add tests/mcp/tools/test_docs_specs_reference.py src/opencode_arch/mcp/tools/docs_specs.py
git commit -m "feat(mcp): architect_docs supports cli_reference/api_reference/plugin_guide"
```

---

## Task 26 — CONTEXT.md refresh (ams)

- Document `WriteBackProjector` + `.llm` naming enforcement
- Document endpoint extraction + Interface subkinds
- Document federated (M3) materializer completion
- Update numbers: schema still 2.1, projector count grows to ~60

**Commit:** `docs(context): refresh AMS CONTEXT.md for Phase 4 write-back + endpoints + M3`

---

## Task 27 — CONTEXT.md refresh (oca)

- Document `architect_propose` tool
- Document per-projector LLM policy
- Document cross-repo trigger templates
- Reference federated MCP surfaces

**Commit:** `docs(context): refresh OCA CONTEXT.md for Phase 4 propose + triggers`

---

## Task 28 — Full-suite verification

Both repos green, all Phases 1–4 tests passing. Live LLM tests remain gated behind `AMS_RUN_LLM_INTEGRATION=1`. @superpowers:verification-before-completion.

**Expected:**
- ams: baseline + Phase 1 + Phase 2 + Phase 3 + ~50 Phase-4 tests, all passing.
- oca: baseline + Phase 1 + Phase 2 + Phase 3 + ~15 Phase-4 tests, all passing.

---

## Rollback Strategy

Each task is one commit. Federated and write-back tracks are independent — if federated design proves flawed, revert Tasks 16–19 without disturbing 1–15 or 20+. Write-back projectors are `.llm` suffixed and separately registered; deterministic siblings continue to work if a write-back variant is reverted.

## Deferred (post-Phase-4 backlog)

- Additional write-back projectors for remaining families (2, 5, 8).
- LLM caching / response memoization (per-prompt-hash cache to avoid repeat costs).
- Cross-repo entity resolution UI (browse into federated child entity from parent).
- Federated migration CLI (upgrade a federated parent + all children in one pass).
- IDE watcher process (deferred from Phase 2; may leverage the Phase-4 filesystem watcher template as base).
