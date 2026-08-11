# Component: Pipeline (COMP-2)

**Status:** Status.ACTIVE
**Description:** —

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/cli/main.py` | — | — |
| `src/architecture_model/pipeline/allocate.py` | — | — |
| `src/architecture_model/pipeline/allocate_types.py` | — | — |
| `src/architecture_model/pipeline/artifacts.py` | — | — |
| `src/architecture_model/pipeline/context_gen.py` | — | — |
| `src/architecture_model/pipeline/contract.py` | — | — |
| `src/architecture_model/pipeline/contract_types.py` | — | — |
| `src/architecture_model/pipeline/coordinator.py` | — | — |
| `src/architecture_model/pipeline/corrections.py` | — | — |
| `src/architecture_model/pipeline/infer.py` | — | — |
| `src/architecture_model/pipeline/infer_types.py` | — | — |
| `src/architecture_model/pipeline/learning.py` | — | — |
| `src/architecture_model/pipeline/observe.py` | — | — |
| `src/architecture_model/pipeline/observe_types.py` | — | — |
| `src/architecture_model/pipeline/protocol.py` | — | — |
| `src/architecture_model/pipeline/regen_score.py` | — | — |
| `src/architecture_model/pipeline/relate.py` | — | — |
| `src/architecture_model/pipeline/relate_types.py` | — | — |
| `src/architecture_model/pipeline/specify.py` | — | — |
| `src/architecture_model/pipeline/specify_types.py` | — | — |
| `src/architecture_model/pipeline/validate.py` | — | — |
| `src/architecture_model/pipeline/validate_types.py` | — | — |

## Responsibilities

- run
- run
- resolve order
- run to
- run stage
- run all
- get prior evidence
- get calibration
- run recursive
- run
- direction
- add correction
- get corrections
- corrections as evidence
- set calibration
- get calibration
- record run
- get trend
- add resolution
- get resolutions
- run
- confidence
- passes
- has
- get
- run
- can run
- output path
- run
- can run
- output path
- run
- run
- run

## Relationships

### Dependencies (outgoing)

None

### Dependents (incoming)

None

## Behaviors Realized

None

## Public API

| Function | Parameters | Returns | Description |
|----------|-----------|---------|-------------|
| `main` | `argv: list[str] | None` | `int` |  |
| `run` | `ctx: PipelineContext` | `StageResult[AllocationResult]` |  |
| `write_artifacts` | `ctx: PipelineContext` | `Path` | Write all pipeline artifacts to output_dir.

Returns the output directory path. |
| `generate_context` | `ctx: PipelineContext` | `str` | Generate context.md content from pipeline results. |
| `write_context` | `ctx: PipelineContext` | `Path` | Write context.md to the output directory. |
| `run` | `ctx: PipelineContext` | `StageResult[ContractResult]` |  |
| `resolve_order` | `target: str` | `list[str]` | Topological sort of deps needed to reach target. |
| `run_to` | `target: str, ctx: PipelineContext` | `dict[str, StageResult]` | Run minimum stages to produce target. Skips cached. |
| `run_stage` | `stage_name: str, ctx: PipelineContext` | `StageResult` | Run single stage + its deps. Returns target's result. |
| `run_all` | `ctx: PipelineContext` | `dict[str, StageResult]` | Run all stages in dep order. Detects circular deps. |
| `get_prior_evidence` | `` | `list` | Get corrections from learning store as prior evidence for stages. |
| `get_calibration` | `module: str` | `dict[str, float]` | Get calibration overrides for a module. |
| `run_recursive` | `ctx: PipelineContext, max_depth: int, leaf_threshold: int` | `dict[str, Any]` | Run all stages, write artifacts, then recurse into large components.

For each component with more files than leaf_threshold, creates a
sub-context scoped to that component's files and re-runs the pipeline.
Artifacts are written at each level. |
| `get_corrections_for_stage` | `ctx: PipelineContext, stage_name: str` | `list[Correction]` | Return corrections applicable to *stage_name* from the LearningStore.

Falls back to an empty list when no store is attached. |
| `run` | `ctx: PipelineContext` | `StageResult[InferenceResult]` |  |
| `direction` | `` | `str` |  |
| `add_correction` | `correction: Correction` | `None` |  |
| `get_corrections` | `module: str | None` | `list[Correction]` |  |
| `corrections_as_evidence` | `` | `list[Evidence]` |  |
| `set_calibration` | `module: str, parameter: str, value: float, reason: str` | `None` |  |
| `get_calibration` | `module: str` | `dict[str, float]` |  |
| `record_run` | `date: str, scores: dict[str, float]` | `None` |  |
| `get_trend` | `module: str` | `QualityTrend` |  |
| `add_resolution` | `outcome: ResolutionOutcome` | `None` |  |
| `get_resolutions` | `category: str | None` | `list[ResolutionOutcome]` |  |
| `run` | `ctx: PipelineContext` | `StageResult[Inventory]` |  |
| `confidence` | `` | `float` |  |
| `passes` | `` | `bool` |  |
| `has` | `stage_name: str` | `bool` |  |
| `get` | `stage_name: str` | `StageResult | None` |  |
| `run` | `context: PipelineContext` | `StageResult[T]` |  |
| `can_run` | `context: PipelineContext` | `bool` |  |
| `output_path` | `context: PipelineContext` | `Path` |  |
| `run` | `ctx: PipelineContext` | `StageResult[RegenScoreResult]` |  |
| `can_run` | `ctx: PipelineContext` | `bool` |  |
| `output_path` | `ctx: PipelineContext` | `Path` |  |
| `run` | `ctx: PipelineContext` | `StageResult[RelateResult]` |  |
| `run` | `ctx: PipelineContext` | `StageResult[SpecifyResult]` |  |
| `run` | `ctx: PipelineContext` | `StageResult[ValidateResult]` |  |

## Interface Dependencies

- **requires** `uses_Manifest` → COMP-3 (Manifest) [load_config, discover_config, get_config, write_config]
- **requires** `uses_Core` → COMP-4 (Core) [load_block_model, load_model, validate_model_data, dump_model, save_model]
- **requires** `uses_Authoring` → COMP-1 (Authoring) [parse_requirements_doc]
- **requires** `uses_Extract` → COMP-6 (Extract) [detect_routes, RouteInfo]

## Patterns

- pipeline

## Confidence

100%
