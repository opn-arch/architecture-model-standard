# Component: Core (COMP-CORE)

**Status:** Status.ACTIVE
**Description:** Central library — type system, parser, validator, slicer, differ, merger, decomposer, coverage, Mermaid visualization

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/core/coverage.py` | — | — |
| `src/architecture_model/core/decomposer.py` | — | — |
| `src/architecture_model/core/differ.py` | — | — |
| `src/architecture_model/core/merger.py` | — | — |
| `src/architecture_model/core/parser.py` | — | — |
| `src/architecture_model/core/slicer.py` | — | — |
| `src/architecture_model/core/types.py` | — | — |
| `src/architecture_model/core/validator.py` | — | — |
| `src/architecture_model/core/visualize.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| CAP-PARSE-VALIDATE | realizes | — |
| CAP-SLICE-DIFF | realizes | — |
| CAP-VISUALIZE | realizes | — |
| IF-LOAD-MODEL | exposes | — |
| IF-VALIDATE-MODEL | exposes | — |
| IF-SLICE-FBLOCK | exposes | — |
| IF-COVERAGE-REPORT | exposes | — |
| IF-GENERATE-DIAGRAMS | exposes | — |
| COMP-UTILS (Utils) | depends-on | — |
| COMP-PROFILES (Profiles) | depends-on | — |
| COMP-SPEC (Spec) | depends-on | — |
| COMP-CONFIG (Config) | depends-on | — |
| COMP-MANIFEST (Manifest) | depends-on | — |
| LAYER-LIB | allocated-to | — |
| CON-ROUND-TRIP | constrained-by | — |

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| COMP-CLI (CLI) | depends-on | — |
| COMP-ORCHESTRATION (Orchestration) | depends-on | — |
| COMP-EXTRACT (Extract) | depends-on | — |
| COMP-MANIFEST (Manifest) | depends-on | — |
| BEH-VALIDATE | traces-to | — |
| BEH-SLICE | traces-to | — |
| BEH-DIFF | traces-to | — |
| BEH-COVERAGE | traces-to | — |
| BEH-VISUALIZE | traces-to | — |

## Behaviors Realized

None

## Public API

| Function | Parameters | Returns | Description |
|----------|-----------|---------|-------------|
| `CoverageResult.summary` | `` | `str` | lines = ['Model Coverage Report', '=' * 40]; for c in self.checks:
    status = '✓' if c.score == 100 else '△' if c.score >= 80 else '✗'
    lines.append(f'  {status} {c.name}: {c.matched}/{c.total} ({c.score:.0f}%)')
    for m in c.missing:
        lines.append(f'      ⚠ Missing: {m}')
    for e in c.extra:
        lines.append(f'      ⊕ Extra (not in code): {e}'); lines.append(f'\nOverall accuracy: {self.overall_score:.0f}%'); return '\n'.join(lines) |
| `coverage_report` | `model: 'ArchitectureModel', manifest: dict` | `CoverageResult` | checks = [_check_component_coverage(model, manifest), _check_relationship_accuracy(model, manifest), _check_capability_coverage(model, manifest), _check_interface_coverage(model, manifest), _check_staleness(model, manifest)]; overall = sum((c.score for c in checks)) / len(checks) if checks else 0.0; return CoverageResult(checks=checks, overall_score=overall) |
| `compute_complexity` | `comp: Component, model: ArchitectureModel` | `float` | symbol_weight = len(comp.symbols) * 2.0; member_weight = sum((len(s.members) for s in comp.symbols)) * 0.3; function_weight = len(comp.functions) * 0.5; deps = sum((1 for r in model.relationships if r.type == Relation...; dep_weight = deps * 1.5; return symbol_weight + member_weight + function_weight + dep_weight |
| `identify_systems` | `model: ArchitectureModel, manifest: dict` | `list[SystemCandidate]` | groups: dict[str, list[Component]] = defaultdict(list); for comp in model.entities.components: ...; fblocks_meta = manifest.get('functional_blocks', {}); candidates: list[SystemCandidate] = []; for (fblock_id, components) in groups.items(): ...; return candidates |
| `auto_assign_f_blocks` | `model: ArchitectureModel, max_cluster_size: int` | `ArchitectureModel` | has_fblocks = any((c.f_block for c in model.entities.components)); if has_fblocks: ...; comps = model.entities.components; if len(comps) <= 1: ...; adj: dict[str, set[str]] = defaultdict(set); comp_ids = {c.id for c in comps}; for rel in model.relationships: ...; sorted_comps = sorted(comps, key=lambda c: len(adj.get(c.id, set())), re...; assigned: dict[str, str] = {}; cluster_id = 0; for comp in sorted_comps: ...; for comp in comps: ...; from copy import deepcopy; new_comps = []; for comp in comps: ...; new_entities = Entities(actors=model.entities.actors, capabilities=model...; return ArchitectureModel(meta=model.meta, entities=new_entities, relationships=model.relationships) |
| `decompose_model` | `model: ArchitectureModel, manifest: dict, output_dir: str` | `DecompositionResult` | candidates = identify_systems(model, manifest); if not candidates: ...; comp_to_system: dict[str, str] = {}; system_ids: dict[str, SystemCandidate] = {}; for candidate in candidates: ...; promoted_comp_ids = set(comp_to_system.keys()); top_level_components = [c for c in model.entities.components if c.id not in prom...; sub_models: dict[str, ArchitectureModel] = {}; systems: list[System] = []; for (sys_id, candidate) in system_ids.items(): ...; top_level_rels: list[Relationship] = []; promoted_rel_keys: set[tuple[RelationType, str, str]] = s...; for rel in model.relationships: ...; top_level_entities = Entities(actors=model.entities.actors, capabilities=model...; top_level_model = ArchitectureModel(meta=model.meta, entities=top_level_ent...; return DecompositionResult(top_level=top_level_model, sub_models=sub_models) |
| `test_affinity_decompose` | `repo_path: Path` | `list[Subsystem]` | test_files = _discover_test_files(repo_path); source_files = _discover_source_files(repo_path); if not source_files: ...; test_to_sources: dict[str, set[Path]] = {}; test_name_to_file: dict[str, Path] = {}; for test_file in test_files: ...; source_claimants: dict[Path, list[str]] = defaultdict(list); for (sub_name, sources) in test_to_sources.items(): ...; source_assignment: dict[Path, str] = {}; for (src_file, claimants) in source_claimants.items(): ...; subsystem_sources: dict[str, set[Path]] = defaultdict(set); subsystem_tests: dict[str, set[Path]] = defaultdict(set); for (src_file, sub_name) in source_assignment.items(): ...; for (sub_name, test_file) in test_name_to_file.items(): ...; for test_file in test_files: ...; for src_file in source_files: ...; if 'root' not in subsystem_sources: ...; source_to_subsystem: dict[Path, str] = {}; for (sub_name, sources) in subsystem_sources.items(): ...; subsystem_deps: dict[str, set[str]] = defaultdict(set); for (sub_name, sources) in subsystem_sources.items(): ...; all_names = set(subsystem_sources.keys()); if not subsystem_sources.get('root'): ...; in_degree: dict[str, int] = {}; for name in all_names: ...; queue = sorted([n for n in all_names if in_degree[n] == 0]); sorted_names: list[str] = []; while queue: ...; remaining = sorted(all_names - set(sorted_names)); sorted_names.extend(remaining); result: list[Subsystem] = []; for sub_name in sorted_names: ...; return result |
| `ModelDiff.has_changes` | `` | `bool` | return bool(self.entity_changes or self.relationship_changes) |
| `ModelDiff.added_count` | `` | `int` | return sum((1 for c in self.entity_changes if c.change_type == ChangeType.ADDED)) |
| `ModelDiff.removed_count` | `` | `int` | return sum((1 for c in self.entity_changes if c.change_type == ChangeType.REMOVED)) |
| `ModelDiff.modified_count` | `` | `int` | return sum((1 for c in self.entity_changes if c.change_type == ChangeType.MODIFIED)) |
| `ModelDiff.summary` | `` | `str` | if not self.has_changes:
    return 'No changes detected.'; return f'Changes: +{self.added_count} -{self.removed_count} ~{self.modified_count} entities, {len(self.relationship_changes)} relationship changes' |
| `ModelDiff.format_report` | `` | `str` | if not self.has_changes:
    return 'No changes detected between model versions.'; lines: list[str] = ['# Architecture Model Diff', '', self.summary(), '']; if self.entity_changes:
    lines.append('## Entity Changes')
    lines.append('')
    by_type: dict[str, list[EntityChange]] = {}
    for change in self.entity_changes:
        by_type.setdefault(change.entity_type, []).append(change)
    for etype, changes in sorted(by_type.items()):
        lines.append(f'### {etype.title()}s')
        for c in changes:
            prefix = {'added': '+', 'removed': '-', 'modified': '~'}[c.change_type.value]
            detail = f' ({c.details})' if c.details else ''
            lines.append(f'  {prefix} {c.entity_id}: {c.entity_name}{detail}')
        lines.append(''); if self.relationship_changes:
    lines.append('## Relationship Changes')
    lines.append('')
    for rc in self.relationship_changes:
        prefix = {'added': '+', 'removed': '-', 'modified': '~'}[rc.change_type.value]
        lines.append(f'  {prefix} {rc.from_id} --{rc.rel_type}--> {rc.to_id}'); return '\n'.join(lines) |
| `ModelDiff.affected_artifacts` | `` | `set[str]` | affected: set[str] = set(); for change in self.entity_changes:
    etype = change.entity_type
    if etype in ('actor', 'behavior'):
        affected.add('use-cases')
    if etype == 'capability':
        affected.add('functional-architecture')
        affected.add('use-cases')
    if etype in ('layer', 'component'):
        affected.add('logical-architecture')
    if etype == 'interface':
        affected.add('icd')
    if etype == 'constraint':
        affected.add('requirements-analysis')
    affected.add('readme'); return affected |
| `diff_models` | `old_model: ArchitectureModel, new_model: ArchitectureModel` | `ModelDiff` | result = ModelDiff(); _diff_entity_list(old_model.entities.actors, new_model.entities.actors, 'actor', result); _diff_entity_list(old_model.entities.capabilities, new_model.entities.capabilities, 'capability', result); _diff_entity_list(old_model.entities.behaviors, new_model.entities.behaviors, 'behavior', result); _diff_entity_list(old_model.entities.interfaces, new_model.entities.interfaces, 'interface', result); _diff_entity_list(old_model.entities.constraints, new_model.entities.constraints, 'constraint', result); _diff_entity_list(old_model.entities.layers, new_model.entities.layers, 'layer', result); _diff_entity_list(old_model.entities.components, new_model.entities.components, 'component', result); _diff_relationships(old_model.relationships, new_model.relationships, result); return result |
| `merge_manifest` | `model: ArchitectureModel, manifest_path: str | Path, project_root: str | Path | None` | `ArchitectureModel` | manifest_path = Path(manifest_path); if not manifest_path.exists(): ...; if project_root is None: ...; manifest = json.loads(manifest_path.read_text(encoding='utf-8')); import hashlib; content = manifest_path.read_bytes(); model.meta.manifest_hash = hashlib.sha256(content).hexdigest()[:16]; _merge_layer_directories(model, manifest, project_root); _merge_component_files(model, manifest); _add_missing_components(model, manifest, project_root); return model |
| `EnrichmentResult.model` | `` | `ArchitectureModel` | return self._model |
| `EnrichmentResult.entities` | `` | `` | return self._model.entities |
| `EnrichmentResult.relationships` | `` | `` | return self._model.relationships |
| `EnrichmentResult.meta` | `` | `` | return self._model.meta |
| `enrich_from_manifest` | `model: ArchitectureModel, manifest: dict` | `EnrichmentResult` | modules = manifest.get('modules', []); interfaces = manifest.get('interfaces', []); stem_to_module: dict[str, dict] = {}; for mod in modules: ...; total_predicted = 0; total_matched = 0; for comp in model.entities.components: ...; _enrich_relationship_imports(model, modules, interfaces, stem_to_module); if total_predicted == 0: ...; return EnrichmentResult(_model=model, naming_accuracy=naming_accuracy) |
| `compact_for_generation` | `model: ArchitectureModel` | `ArchitectureModel` | import copy; import yaml; model = copy.deepcopy(model); n_components = len(model.entities.components); if n_components > 15: ...; for comp in model.entities.components: ...; return model |
| `compose_enriched_model` | `project_root: Path` | `ArchitectureModel` | from architecture_model.manifest.body_hints import extrac...; from architecture_model.manifest.scanner import _parse_fi...; from architecture_model.manifest.test_analyzer import ana...; source_files = discover_source_files(project_root); test_files = discover_test_files(project_root); source_stems = {f.stem for f in source_files}; test_mapping = _map_tests_to_sources(test_files, source_stems, project_r...; components: list[Component] = []; for src_file in source_files: ...; project_name = project_root.name; meta = ModelMeta(schema_version='1.4', project=project_name); entities = Entities(components=components); return ArchitectureModel(meta=meta, entities=entities, relationships=[]) |
| `load_model` | `path: str | Path` | `ArchitectureModel` | path = Path(path); with open(path, 'r', encoding='utf-8') as f:
    raw = yaml.safe_load(f); if raw is None:
    raise ValueError(f'Empty model file: {path}'); return _parse_raw(raw) |
| `validate_model_data` | `data: dict[str, Any]` | `list[str]` | if not HAS_JSONSCHEMA:
    return ['jsonschema not installed — skipping schema validation']; schema = json.loads(SCHEMA_PATH.read_text(encoding='utf-8')); validator = jsonschema.Draft202012Validator(schema); return [f'{e.json_path}: {e.message}' for e in validator.iter_errors(data)] |
| `dump_model` | `model: ArchitectureModel` | `dict[str, Any]` | return {'meta': _dump_meta(model.meta), 'entities': _dump_entities(model.entities), 'relationships': [_dump_relationship(r) for r in model.relationships]} |
| `save_model` | `model: ArchitectureModel, path: str | Path` | `None` | path = Path(path); path.parent.mkdir(parents=True, exist_ok=True); data = dump_model(model); with open(path, 'w', encoding='utf-8') as f:
    yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True, width=120) |
| `slice_by_fblock` | `model: ArchitectureModel, f_block: str, include_relationships: bool` | `ArchitectureModel` | cap_ids = {c.id for c in model.entities.capabilities if c.f_block =...; behaviors = [b for b in model.entities.behaviors if f_block in b.tags]; behavior_ids = {b.id for b in behaviors}; components = [c for c in model.entities.components if c.f_block == f_b...; component_ids = {c.id for c in components}; interfaces = [i for i in model.entities.interfaces if f_block in i.pro...; interface_ids = {i.id for i in interfaces}; relevant_ids = cap_ids | behavior_ids | component_ids | interface_ids; data_entities = [d for d in model.entities.data if d.owner in component_ids]; data_ids = {d.id for d in data_entities}; events = [e for e in model.entities.events if e.source in componen...; event_ids = {e.id for e in events}; quality_attrs = [q for q in model.entities.quality_attributes if any((a i...; qa_ids = {q.id for q in quality_attrs}; relevant_ids = relevant_ids | data_ids | event_ids | qa_ids; actor_refs = set(); for beh in behaviors: ...; actors = [a for a in model.entities.actors if a.id in actor_refs]; relationships = []; if include_relationships: ...; capabilities = [c for c in model.entities.capabilities if c.f_block == f...; return ArchitectureModel(meta=ModelMeta(schema_version=model.meta.schema_version, project=model.meta.project, system=model.meta.system, generated_at=model.meta.generated_at, source_artifacts=model.meta.source_artifacts), entities=Entities(actors=actors, capabilities=capabilities, behaviors=behaviors, interfaces=interfaces, constraints=[], layers=[], components=components, data=data_entities, events=events, quality_attributes=quality_attrs), relationships=relationships) |
| `slice_by_layer` | `model: ArchitectureModel, layer_id: str` | `ArchitectureModel` | layers = [l for l in model.entities.layers if l.id == layer_id]; components = [c for c in model.entities.components if c.layer == layer_id]; component_ids = {c.id for c in components}; relationships = [deepcopy(r) for r in model.relationships if r.from_id in component_ids or r.to_id in component_ids]; return ArchitectureModel(meta=ModelMeta(schema_version=model.meta.schema_version, project=model.meta.project, system=model.meta.system, generated_at=model.meta.generated_at, source_artifacts=model.meta.source_artifacts), entities=Entities(layers=layers, components=components), relationships=relationships) |
| `slice_by_status` | `model: ArchitectureModel, status: Status` | `ArchitectureModel` | entities = Entities(actors=[a for a in model.entities.actors if a.status == status], capabilities=[c for c in model.entities.capabilities if c.status == status], behaviors=[b for b in model.entities.behaviors if b.status == status], interfaces=[i for i in model.entities.interfaces if i.status == status], constraints=[c for c in model.entities.constraints if c.status == status], layers=[l for l in model.entities.layers if l.status == status], components=[c for c in model.entities.components if c.status == status], systems=[s for s in model.entities.systems if s.status == status], data=[d for d in model.entities.data if d.status == status], events=[e for e in model.entities.events if e.status == status], resources=[r for r in model.entities.resources if r.status == status], environments=[e for e in model.entities.environments if e.status == status], quality_attributes=[q for q in model.entities.quality_attributes if q.status == status], decisions=[d for d in model.entities.decisions if d.status == status], lifecycles=[l for l in model.entities.lifecycles if l.status == status]); all_ids = set(); for attr_name in ['actors', 'capabilities', 'behaviors', 'interfaces', 'constraints', 'layers', 'components', 'systems', 'data', 'events', 'resources', 'environments', 'quality_attributes', 'decisions', 'lifecycles']:
    for e in getattr(entities, attr_name, []):
        all_ids.add(e.id); relationships = [deepcopy(r) for r in model.relationships if r.from_id in all_ids and r.to_id in all_ids]; return ArchitectureModel(meta=deepcopy(model.meta), entities=entities, relationships=relationships) |
| `slice_for_artifact` | `model: ArchitectureModel, artifact_name: str` | `ArchitectureModel` | slicers = {'functional-architecture': _slice_for_functional, 'logical-architecture': _slice_for_logical, 'use-cases': _slice_for_use_cases, 'icd': _slice_for_icd, 'requirements-analysis': _slice_for_requirements, 'operations-manual': _slice_for_operations_manual, 'conops': _slice_for_conops, 'testing': _slice_for_testing, 'deployment-guide': _slice_for_deployment, 'data-dictionary': _slice_for_data_dictionary, 'readme': _slice_for_readme}; slicer_fn = slicers.get(artifact_name); if slicer_fn:
    return slicer_fn(model); return deepcopy(model) |
| `RelationType.parse` | `value: str` | `RelationType | str` | try:
    return cls(value)
except ValueError:
    return value |
| `ActorType.parse` | `value: str` | `ActorType | str` | try:
    return cls(value)
except ValueError:
    return value |
| `InterfaceType.parse` | `value: str` | `InterfaceType | str` | try:
    return cls(value)
except ValueError:
    return value |
| `ConstraintType.parse` | `value: str` | `ConstraintType | str` | try:
    return cls(value)
except ValueError:
    return value |
| `ComponentKind.parse` | `value: str` | `ComponentKind | str` | try:
    return cls(value)
except ValueError:
    return value |
| `BehaviorPattern.parse` | `value: str` | `BehaviorPattern | str` | try:
    return cls(value)
except ValueError:
    return value |
| `EventKind.parse` | `value: str` | `EventKind | str` | try:
    return cls(value)
except ValueError:
    return value |
| `ResourceKind.parse` | `value: str` | `ResourceKind | str` | try:
    return cls(value)
except ValueError:
    return value |
| `EnvironmentKind.parse` | `value: str` | `EnvironmentKind | str` | try:
    return cls(value)
except ValueError:
    return value |
| `DecisionStatus.parse` | `value: str` | `DecisionStatus | str` | try:
    return cls(value)
except ValueError:
    return value |
| `LifecyclePhase.parse` | `value: str` | `LifecyclePhase | str` | try:
    return cls(value)
except ValueError:
    return value |
| `ArchitectureModel.all_entity_ids` | `` | `set[str]` | ids: set[str] = set(); for actor in self.entities.actors: ...; for cap in self.entities.capabilities: ...; for beh in self.entities.behaviors: ...; for iface in self.entities.interfaces: ...; for con in self.entities.constraints: ...; for layer in self.entities.layers: ...; for comp in self.entities.components: ...; for sys in self.entities.systems: ...; for d in self.entities.data: ...; for e in self.entities.events: ...; for r in self.entities.resources: ...; for e in self.entities.environments: ...; for qa in self.entities.quality_attributes: ...; for d in self.entities.decisions: ...; for lc in self.entities.lifecycles: ...; return ids |
| `ArchitectureModel.entity_count` | `` | `int` | return len(self.all_entity_ids) |
| `ArchitectureModel.relationship_count` | `` | `int` | return len(self.relationships) |
| `ArchitectureModel.to_dict` | `` | `dict[str, Any]` | return {'meta': self._dump_meta(), 'entities': self._dump_entities(), 'relationships': [self._dump_relationship(r) for r in self.relationships]} |
| `ArchitectureModel.to_yaml` | `` | `str` | return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False) |
| `ValidationResult.error_count` | `` | `int` | return sum((1 for i in self.issues if i.severity == Severity.ERROR)) |
| `ValidationResult.warning_count` | `` | `int` | return sum((1 for i in self.issues if i.severity == Severity.WARNING)) |
| `ValidationResult.info_count` | `` | `int` | return sum((1 for i in self.issues if i.severity == Severity.INFO)) |
| `ValidationResult.is_valid` | `` | `bool` | return self.error_count == 0 |
| `ValidationResult.score` | `` | `int` | penalty = self.error_count * 10 + self.warning_count * 2; return max(0, 100 - penalty) |
| `ValidationResult.summary` | `` | `str` | return f'Score: {self.score}/100 | Errors: {self.error_count}, Warnings: {self.warning_count}, Info: {self.info_count}' |
| `validate_model` | `model: ArchitectureModel, strict: bool` | `ValidationResult` | result = ValidationResult(); _check_id_uniqueness(model, result); _check_referential_integrity(model, result); _check_orphan_entities(model, result); _check_status_consistency(model, result); _check_capability_realization(model, result); _check_meta_completeness(model, result); _check_v11_semantics(model, result); _check_regen_readiness(model, result); _check_domain_profile(model, result); _check_improvement_opportunities(model, result); if strict: ...; return result |
| `generate_context_diagram` | `model: 'ArchitectureModel'` | `str` | lines = ['flowchart TB']; project = getattr(model.meta, 'project', 'System'); lines.append(f'    subgraph system[{_label(project)}]'); for ifc in model.entities.interfaces: ...; if not model.entities.interfaces: ...; lines.append('    end'); for actor in model.entities.actors: ...; for rel in model.relationships: ...; return '\n'.join(lines) |
| `generate_components_diagram` | `model: 'ArchitectureModel'` | `str` | lines = ['flowchart TB']; layer_ids = {l.id for l in model.entities.layers}; comp_ids = {c.id for c in model.entities.components}; layer_members: dict[str, list[str]] = defaultdict(list); for rel in model.relationships: ...; assigned = {cid for members in layer_members.values() for cid in mem...; unassigned = [c for c in model.entities.components if c.id not in assi...; layer_map = {l.id: l for l in model.entities.layers}; for lid in sorted(layer_members): ...; if unassigned: ...; for cap in model.entities.capabilities: ...; for rel in model.relationships: ...; return '\n'.join(lines) |
| `generate_behaviors_diagram` | `model: 'ArchitectureModel'` | `str` | lines = ['flowchart LR']; beh_ids = {b.id for b in model.entities.behaviors}; for beh in model.entities.behaviors: ...; for rel in model.relationships: ...; for rel in model.relationships: ...; return '\n'.join(lines) |
| `generate_dependencies_diagram` | `model: 'ArchitectureModel'` | `str` | lines = ['flowchart LR']; fblock_groups: dict[str, list] = defaultdict(list); for comp in model.entities.components: ...; fblock_names: dict[str, str] = {}; for cap in model.entities.capabilities: ...; for fb in sorted(fblock_groups): ...; for rel in model.relationships: ...; return '\n'.join(lines) |
| `generate_all_diagrams` | `model: 'ArchitectureModel', output_dir: Path` | `dict[str, Path]` | output_dir.mkdir(parents=True, exist_ok=True); generators = {'context': generate_context_diagram, 'components': generate_components_diagram, 'behaviors': generate_behaviors_diagram, 'dependencies': generate_dependencies_diagram}; paths = {}; for name, gen_fn in generators.items():
    content = gen_fn(model)
    path = output_dir / f'{name}.mmd'
    path.write_text(content + '\n')
    paths[name] = path; return paths |

## Patterns

None

## Confidence

0%


---

# Component: Manifest (COMP-MANIFEST)

**Status:** Status.ACTIVE
**Description:** Reality Manifest Generator — AST scanning, body hints, test contracts, metrics, recursive manifests, typed dataclasses

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/manifest/blocks.py` | — | — |
| `src/architecture_model/manifest/body_hints.py` | — | — |
| `src/architecture_model/manifest/display.py` | — | — |
| `src/architecture_model/manifest/generator.py` | — | — |
| `src/architecture_model/manifest/interfaces.py` | — | — |
| `src/architecture_model/manifest/metrics.py` | — | — |
| `src/architecture_model/manifest/recursive.py` | — | — |
| `src/architecture_model/manifest/scanner.py` | — | — |
| `src/architecture_model/manifest/slicers.py` | — | — |
| `src/architecture_model/manifest/test_analyzer.py` | — | — |
| `src/architecture_model/manifest/types.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| CAP-MANIFEST | realizes | — |
| IF-GENERATE-MANIFEST | exposes | — |
| COMP-UTILS (Utils) | depends-on | — |
| COMP-CONFIG (Config) | depends-on | — |
| COMP-CORE (Core) | depends-on | — |
| LAYER-LIB | allocated-to | — |

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| COMP-CLI (CLI) | depends-on | — |
| COMP-ORCHESTRATION (Orchestration) | depends-on | — |
| COMP-EXTRACT (Extract) | depends-on | — |
| COMP-CORE (Core) | depends-on | — |
| BEH-MANIFEST | traces-to | — |

## Behaviors Realized

None

## Public API

| Function | Parameters | Returns | Description |
|----------|-----------|---------|-------------|
| `process_block` | `root: Path, block_id: str, block_def: dict, sub_block_configs: list | None` | `BlockManifest` | sub_functions: list[SubFunctionEntry] = []; all_files: list[Path] = []; for dir_path in block_def['dirs']: ...; for file_path in block_def['files']: ...; logger.debug('Block %s: %d files from %d dirs', block_id, len(all_files), len(block_def['dirs'])); for (idx, filepath) in enumerate(all_files, 1): ...; block_status = 'active' if any((sf.status == 'active' for sf in sub_func...; sub_blocks_manifest: list[dict[str, Any]] = []; if sub_block_configs: ...; logger.debug('Block %s: %d sub_functions, %d sub_blocks', block_id, len(sub_functions), len(sub_blocks_manifest)); return BlockManifest(name=block_def['name'], status=block_status, description_source=block_def['description_source'], sub_functions=sub_functions, sub_blocks=sub_blocks_manifest) |
| `classify_function` | `source: str, func_name: str` | `BodyComplexity` | tree = ast.parse(source); node = _find_function(tree, func_name); body = _strip_docstring(node.body); count = len(body); if count <= 1:
    return BodyComplexity.TRIVIAL
elif count <= 5:
    return BodyComplexity.SHORT
else:
    return BodyComplexity.COMPLEX |
| `extract_body_hint` | `source: str, func_name: str, class_name: str | None` | `str` | tree = ast.parse(source); node = _find_function(tree, func_name, class_name); body = _strip_docstring(node.body); count = len(body); if count <= 1:
    return ast.unparse(body[0]) if body else ''
elif count <= 5:
    return '; '.join((ast.unparse(s) for s in body))
else:
    return _summarize_complex_body(body) |
| `extract_file_hints` | `filepath: Path, include_private: bool` | `list[FunctionSignature]` | source = filepath.read_text(encoding='utf-8'); tree = ast.parse(source, filename=str(filepath)); results: list[FunctionSignature] = []; def _should_include(name: str) -> bool:
    if include_pr...; for node in ast.iter_child_nodes(tree): ...; return results |
| `print_summary` | `manifest: dict[str, Any]` | `None` | metrics = manifest['metrics']; blocks = manifest['functional_blocks']; print(f'\n{'=' * 60}'); print('REALITY MANIFEST SUMMARY'); print(f'{'=' * 60}'); print(f'  Generated: {manifest['generated_at']}'); print(f'  Root:      {manifest['project_root']}'); print(); print('  METRICS:'); known_labels = ['router', 'model', 'migration', 'template']; shown = False; for label in known_labels: ...; for (key, val) in metrics.items(): ...; if not shown: ...; print(f'    Python files: {metrics.get('total_python_files', 'N/A')}'); print(); print('  FUNCTIONAL BLOCKS:'); for (block_id, block) in blocks.items(): ...; print(); print(f'  INTERFACES: {len(manifest.get('interfaces', []))} dependencies detected'); print(f'  MODULES:    {len(manifest.get('modules', []))} files scanned'); print(f'{'=' * 60}') |
| `generate_manifest` | `project_root: Path, config: Optional[Any]` | `Manifest` | root = project_root.resolve(); report = ScanReport(); if config is None: ...; logger.info('Computing project metrics for %s', root); metrics_result = compute_metrics(root, config); logger.info('Metrics computed: %s', metrics_result.values); blocks_dict = config.fblock_dict; logger.info('Processing %d functional blocks', len(blocks_dict)); from architecture_model.manifest.types import BlockManifest; functional_blocks: dict[str, BlockManifest] = {}; scanned_files: set[str] = set(); for (block_id, block_def) in blocks_dict.items(): ...; logger.info('Processed %d blocks, found %d files', report.blocks_processed, len(scanned_files)); extra_dirs: set[str] = set(); for layer in config.layers: ...; for dir_path in sorted(extra_dirs): ...; logger.info('Scanning %d files for module metadata', len(scanned_files)); from architecture_model.manifest.types import ModuleInfo; all_modules: list[ModuleInfo] = []; for rel_path in sorted(scanned_files): ...; logger.info('Deriving interfaces from %d modules', len(all_modules)); interfaces = derive_interfaces(all_modules, root); report.interfaces_derived = len(interfaces); report.log_summary(); return Manifest(generated_at=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S'), project_root=str(root), metrics=metrics_result, functional_blocks=functional_blocks, modules=all_modules, interfaces=interfaces, scan_report=report) |
| `load_or_generate_manifest` | `project_root: Path, output_dir: Path | None` | `dict[str, Any]` | from architecture_model.config.loader import get_config; config = get_config(project_root); if output_dir is None: ...; if manifest_path.exists(): ...; manifest = generate_manifest(project_root, config); manifest_dict = manifest.to_dict(); manifest_path.parent.mkdir(parents=True, exist_ok=True); manifest_path.write_text(json.dumps(manifest_dict, indent=2, ensure_ascii=False), encoding='utf-8'); return manifest_dict |
| `derive_interfaces` | `modules: list[ModuleInfo], root: Path` | `list[InterfaceEdge]` | file_to_module: dict[str, str] = {}; for mod in modules: ...; module_to_file: dict[str, str] = {v: k for k, v in file_t...; file_set: set[str] = {f.removesuffix('.py') for f in file...; interfaces: list[InterfaceEdge] = []; seen: set[tuple[str, str]] = set(); def _add_edge(source: str, target: str, import_path: str)...; def _resolve_dotted(dotted: str) -> str | None:
    """Re...; for mod in modules: ...; logger.debug('Derived %d interface edges from %d modules', len(interfaces), len(modules)); return interfaces |
| `compute_metrics` | `root: Path, config: Optional[Any]` | `MetricsResult` | if config is None: ...; result: dict[str, int] = {}; for metric in config.metrics: ...; total_python = len([p for p in root.rglob('*.py') if not any((part in EX...; result['total_python_files'] = total_python; logger.debug('Computed %d metrics for %s: %s', len(result), root, result); return MetricsResult(values=result) |
| `generate_block_manifest` | `root: Path, block_id: str, block_def: dict[str, Any]` | `Manifest` | report = ScanReport(); modules = []; all_files: list[Path] = []; for d in block_def.get('dirs', []): ...; for f in block_def.get('files', []): ...; seen = set(); unique_files = []; for f in all_files: ...; for filepath in sorted(unique_files): ...; interfaces = derive_interfaces(modules, root); report.interfaces_derived = len(interfaces); metrics = MetricsResult(values={'py_files': len(unique_files), 'tot...; return Manifest(generated_at=datetime.now(timezone.utc).isoformat(), project_root=str(root), metrics=metrics, functional_blocks={}, modules=modules, interfaces=interfaces, scan_report=report) |
| `generate_recursive_manifests` | `project_root: Path, parent_model: str` | `dict[str, RecursiveManifest]` | config = get_config(project_root); results: dict[str, RecursiveManifest] = {}; for (block_id, block_def) in config.fblock_dict.items(): ...; block_deps = compute_block_dependencies(results, config); for (block_id, deps) in block_deps.items(): ...; return results |
| `compute_block_dependencies` | `manifests: dict[str, RecursiveManifest], config` | `dict[str, list[str]]` | file_to_block: dict[str, str] = {}; for (block_id, block_def) in config.fblock_dict.items(): ...; def _resolve_import_to_block(slash_path: str) -> str | No...; dependencies: dict[str, list[str]] = {}; for (block_id, rm) in manifests.items(): ...; return dependencies |
| `write_recursive_manifests` | `manifests: dict[str, RecursiveManifest], output_dir: Path` | `list[Path]` | written: list[Path] = []; for block_id, rm in manifests.items():
    block_dir = output_dir / block_id
    block_dir.mkdir(parents=True, exist_ok=True)
    out_path = block_dir / 'manifest.json'
    out_path.write_text(json.dumps(rm.to_dict(), indent=2, default=str), encoding='utf-8')
    written.append(out_path)
    logger.info('Wrote %s', out_path); return written |
| `scan_file` | `root: Path, filepath: Path` | `ModuleInfo` | rel_path = str(filepath.relative_to(root)); line_count = _file_line_count(filepath); status = _determine_status(filepath, line_count); tree = _parse_file_ast(filepath); docstring = None; functions: list[FunctionInfo] = []; imports: list[str] = []; if tree is not None: ...; name = _derive_name_from_docstring(docstring, filepath); logger.debug('Scanned %s: %d funcs, %d classes, %d constants', rel_path, len(functions), len(classes), len(constants)); return ModuleInfo(file=rel_path, name=name, docstring=docstring, functions=functions, imports=imports, line_count=line_count, status=status, classes=classes, exports=exports, decorated_functions=decorated, imports_detailed=imports_detailed, module_constants=constants, module_assignments=assignments) |
| `get_manifest_slice` | `manifest: Manifest | dict[str, Any], artifact_name: str` | `str` | if isinstance(manifest, dict):
    logger.debug('get_manifest_slice received dict, converting to Manifest')
    manifest = _manifest_from_dict(manifest); slicers = {'functional-architecture': _slice_functional_architecture, 'logical-architecture': _slice_logical_architecture, 'data-dictionary': _slice_data_dictionary, 'icd': _slice_icd, 'readme': _slice_readme, 'testing': _slice_testing, 'deployment-guide': _slice_deployment_guide, 'operations-manual': _slice_operations_manual, 'use-cases': _slice_use_cases, 'requirements-analysis': _slice_requirements_analysis}; slicer = slicers.get(artifact_name); if slicer is None:
    return f'[unknown artifact: {artifact_name}]'; return slicer(manifest) |
| `analyze_test_file` | `test_file: Path` | `TestAnalysisResult` | source = test_file.read_text(encoding='utf-8'); tree = ast.parse(source, filename=str(test_file)); filename = test_file.name; result = TestAnalysisResult(test_file=filename); result.required_imports = _extract_imports(tree); test_methods = _find_test_methods(tree); result.test_count = len(test_methods); for (method_name, node) in test_methods: ...; result.constants = extract_constants_from_contracts(result.contracts); return result |
| `extract_constants_from_contracts` | `contracts: list[TestContract]` | `list[Constant]` | constants: list[Constant] = []; seen: set[tuple[str, str]] = set(); for contract in contracts:
    if contract.contract_type != 'value_equality':
        continue
    parsed = _parse_escape_code_assertion(contract.assertion)
    if parsed is None:
        continue
    parent, name, code, full_escape = parsed
    key = (parent, name)
    if key in seen:
        continue
    seen.add(key)
    constants.append(Constant(name=name, value=code, context=f'attribute of {parent}, produces escape code {full_escape}')); return constants |
| `ModuleInfo.to_dict` | `` | `dict[str, Any]` | return {'file': self.file, 'name': self.name, 'docstring': self.docstring, 'functions': [{'name': f.name, 'signature': f.signature, **({'calls': f.calls} if f.calls else {}), **({'docstring': f.docstring} if f.docstring else {}), **({'raises': f.raises} if f.raises else {})} for f in self.functions], 'imports': self.imports, 'line_count': self.line_count, 'status': self.status.value, 'classes': [{'name': c.name, 'bases': c.bases, 'methods': c.methods, 'is_abstract': c.is_abstract, 'decorators': c.decorators, 'attributes': c.attributes} for c in self.classes], 'exports': self.exports, 'decorated_functions': [{'name': d.name, 'decorators': d.decorators, 'is_method': d.is_method, 'class_name': d.class_name} for d in self.decorated_functions], 'imports_detailed': [{'module': i.module, 'symbols': i.symbols, 'is_relative': i.is_relative} for i in self.imports_detailed], 'module_constants': self.module_constants, 'module_assignments': self.module_assignments} |
| `InterfaceEdge.to_dict` | `` | `dict[str, str]` | return {'source': self.source, 'target': self.target, 'import_path': self.import_path} |
| `SubFunctionEntry.to_dict` | `` | `dict[str, Any]` | return {'id': self.id, 'name': self.name, 'file': self.file, 'functions': self.functions, 'inputs': self.inputs, 'outputs': self.outputs, 'status': self.status, 'line_count': self.line_count} |
| `BlockManifest.to_dict` | `` | `dict[str, Any]` | return {'name': self.name, 'status': self.status, 'description_source': self.description_source, 'sub_functions': [sf.to_dict() for sf in self.sub_functions], 'sub_blocks': self.sub_blocks} |
| `MetricsResult.to_dict` | `` | `dict[str, int]` | return dict(self.values) |
| `ScanReport.success_rate` | `` | `float` | if self.files_attempted == 0:
    return 1.0; return self.files_succeeded / self.files_attempted |
| `ScanReport.log_summary` | `` | `None` | logger.info('Scan complete: %d/%d files (%.1f%%), %d funcs, %d classes, %d constants, %d interfaces, %d blocks, %d unclaimed, %d errors', self.files_succeeded, self.files_attempted, self.success_rate * 100, self.functions_extracted, self.classes_extracted, self.constants_extracted, self.interfaces_derived, self.blocks_processed, self.unclaimed_files, len(self.parse_errors)) |
| `Manifest.to_dict` | `` | `dict[str, Any]` | return {'generated_at': self.generated_at, 'project_root': self.project_root, 'metrics': self.metrics.to_dict(), 'functional_blocks': {k: v.to_dict() for k, v in self.functional_blocks.items()}, 'modules': [m.to_dict() for m in self.modules], 'interfaces': [i.to_dict() for i in self.interfaces]} |
| `RecursiveManifest.to_dict` | `` | `dict[str, Any]` | return {'block_id': self.block_id, 'block_name': self.block_name, 'parent_model': self.parent_model, 'component_id': self.component_id, 'manifest': self.manifest.to_dict(), 'children': {k: v.to_dict() for k, v in self.children.items()}, 'block_dependencies': self.block_dependencies} |

## Patterns

None

## Confidence

0%


---

# Component: Config (COMP-CONFIG)

**Status:** Status.ACTIVE
**Description:** Self-bootstrapping configuration — auto-discovery, schema, loader

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/config/loader.py` | — | — |
| `src/architecture_model/config/schema.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| CAP-CONFIG | realizes | — |
| IF-GET-CONFIG | exposes | — |
| COMP-UTILS (Utils) | depends-on | — |
| LAYER-LIB | allocated-to | — |
| CON-SELF-BOOTSTRAP | constrained-by | — |

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| COMP-CLI (CLI) | depends-on | — |
| COMP-ORCHESTRATION (Orchestration) | depends-on | — |
| COMP-EXTRACT (Extract) | depends-on | — |
| COMP-CORE (Core) | depends-on | — |
| COMP-MANIFEST (Manifest) | depends-on | — |
| BEH-INIT | traces-to | — |

## Behaviors Realized

None

## Public API

| Function | Parameters | Returns | Description |
|----------|-----------|---------|-------------|
| `load_config` | `root: Path` | `ProjectConfig` | config_path = root / CONFIG_FILENAME; if not config_path.exists():
    raise FileNotFoundError(f'No {CONFIG_FILENAME} found in {root}. Run `architecture-model init` to generate one, or use get_config() for auto-discovery.'); data = yaml.safe_load(config_path.read_text(encoding='utf-8')); if not data:
    data = {}; return ProjectConfig.from_dict(data, root=root) |
| `discover_config` | `root: Path` | `tuple[ProjectConfig, DiscoveryReport]` | name = root.name; report = DiscoveryReport(); layers = _discover_layers(root, report); metrics = _discover_metrics(root); functional_blocks = _discover_functional_blocks(root, report); if not layers and functional_blocks: ...; report.layers_discovered = len(layers); report.metrics_discovered = len(metrics); config = ProjectConfig(name=name, system=name, output=OutputConfig...; logger.info('Discovery complete: %s', report.summary()); return (config, report) |
| `get_config` | `root: Path` | `ProjectConfig` | config_path = root / CONFIG_FILENAME; if config_path.exists():
    config = load_config(root)
    if not config.functional_blocks:
        config, _report = discover_config(root)
        return config
    for block in config.functional_blocks:
        if not block.sub_blocks and block.dirs:
            block_path = root / block.dirs[0]
            if block_path.is_dir():
                block.sub_blocks = _discover_sub_blocks(block_path, block.id, root)
    return config; config, _report = discover_config(root); return config |
| `write_config` | `config: ProjectConfig, root: Path | None` | `Path` | if root is None: ...; config_path = root / CONFIG_FILENAME; data = config.to_dict(); header = "# Architecture Model Standard - Project Descriptor\n# Au...; yaml_content = yaml.dump(data, default_flow_style=False, sort_keys=False...; config_path.write_text(header + yaml_content, encoding='utf-8'); return config_path |
| `OutputConfig.resolve` | `project_name: str, root: Path` | `'ResolvedOutputConfig'` | return ResolvedOutputConfig(model=root / self.model.format(project=project_name), manifest=root / self.manifest.format(project=project_name), artifacts=root / self.artifacts.format(project=project_name)) |
| `ProjectConfig.layer_dir_map` | `` | `dict[str, list[str]]` | return {layer.id: layer.dirs for layer in self.layers if layer.dirs} |
| `ProjectConfig.fblock_dir_map` | `` | `dict[str, str]` | result: dict[str, str] = {}; for block in self.functional_blocks:
    for d in block.dirs:
        result[d] = block.id
    for f in block.files:
        prefix = f.rsplit('.py', 1)[0] if f.endswith('.py') else f
        result[prefix] = block.id; return result |
| `ProjectConfig.fblock_dict` | `` | `dict[str, dict[str, Any]]` | return {block.id: {'name': block.name, 'dirs': block.dirs, 'files': block.files, 'description_source': block.description_source} for block in self.functional_blocks} |
| `ProjectConfig.metrics_paths` | `` | `dict[str, Path]` | return {m.label: self.root / m.path for m in self.metrics} |
| `ProjectConfig.resolved_output` | `` | `ResolvedOutputConfig` | return self.output.resolve(self.name, self.root) |
| `ProjectConfig.from_dict` | `data: dict[str, Any], root: Path` | `'ProjectConfig'` | project = data.get('project', {}); output_data = data.get('output', {}); layers_data = data.get('layers', {}); blocks_data = data.get('functional_blocks', {}); metrics_data = data.get('metrics', []); layers = [LayerConfig(id=layer_id, dirs=layer_def.get('dirs', []) ...; blocks = [FunctionalBlockConfig(id=block_id, name=block_def.get('n...; metrics = [MetricConfig(label=m.get('label', ''), path=m.get('path'...; return cls(name=project.get('name', ''), system=project.get('system', ''), output=OutputConfig(model=output_data.get('model', OutputConfig.model), manifest=output_data.get('manifest', OutputConfig.manifest), artifacts=output_data.get('artifacts', OutputConfig.artifacts)), layers=layers, functional_blocks=blocks, metrics=metrics, root=root) |
| `ProjectConfig.to_dict` | `` | `dict[str, Any]` | return {'project': {'name': self.name, 'system': self.system}, 'output': {'model': self.output.model, 'manifest': self.output.manifest, 'artifacts': self.output.artifacts}, 'layers': {layer.id: {'dirs': layer.dirs} for layer in self.layers}, 'functional_blocks': {block.id: {'name': block.name, 'dirs': block.dirs, 'files': block.files, 'description_source': block.description_source, **({'sub_blocks': _serialize_sub_blocks(block.sub_blocks)} if block.sub_blocks else {})} for block in self.functional_blocks}, 'metrics': [{'label': m.label, 'path': m.path, 'pattern': m.pattern, **({'exclude': m.exclude} if m.exclude else {}), **({'recursive': True} if m.recursive else {})} for m in self.metrics]} |
| `DiscoveryReport.add_candidate` | `category: str, path: str, accepted: bool, reason: str` | `None` | self.candidates.append(DiscoveryCandidate(category, path, accepted, reason)) |
| `DiscoveryReport.claim_rate` | `` | `float` | if self.files_total == 0:
    return 1.0; return self.files_claimed / self.files_total |
| `DiscoveryReport.summary` | `` | `str` | return f'Layout: {self.layout_detected}, {self.blocks_discovered} blocks, {self.layers_discovered} layers, {self.metrics_discovered} metrics, {self.files_claimed}/{self.files_total} files claimed ({self.claim_rate:.0%})' |

## Patterns

None

## Confidence

0%


---

# Component: CLI (COMP-CLI)

**Status:** Status.ACTIVE
**Description:** Command-line interface — argparse dispatch, Mermaid visualization shim

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/cli/main.py` | — | — |
| `src/architecture_model/cli/visualize.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| CAP-CLI | realizes | — |
| IF-CLI-MAIN | exposes | — |
| COMP-CORE (Core) | depends-on | — |
| COMP-CONFIG (Config) | depends-on | — |
| COMP-MANIFEST (Manifest) | depends-on | — |
| COMP-ORCHESTRATION (Orchestration) | depends-on | — |
| LAYER-UI | allocated-to | — |

### Dependents (incoming)

None

## Behaviors Realized

None

## Public API

| Function | Parameters | Returns | Description |
|----------|-----------|---------|-------------|
| `main` | `argv: list[str] | None` | `int` | parser = argparse.ArgumentParser(prog='architecture-model', descri...; subparsers = parser.add_subparsers(dest='command', help='Available com...; p_validate = subparsers.add_parser('validate', help='Validate model in...; p_validate.add_argument('model', help='Path to architecture-model.yaml'); p_validate.add_argument('--strict', action='store_true', help='Promote warnings to errors'); p_slice = subparsers.add_parser('slice', help='Extract model subset'); p_slice.add_argument('model', help='Path to architecture-model.yaml'); p_slice.add_argument('--fblock', help='Filter by F-block (e.g., F3)'); p_slice.add_argument('--layer', help='Filter by layer (e.g., web-layer)'); p_slice.add_argument('--artifact', help='Slice for artifact regeneration'); p_slice.add_argument('--status', help='Filter by status (ACTIVE, PLANNED)'); p_slice.add_argument('-o', '--output', help='Output YAML path (default: stdout summary)'); p_diff = subparsers.add_parser('diff', help='Compare two model ver...; p_diff.add_argument('old_model', help='Path to old/baseline model'); p_diff.add_argument('new_model', help='Path to new/current model'); p_stats = subparsers.add_parser('stats', help='Show model statistics'); p_stats.add_argument('model', help='Path to architecture-model.yaml'); p_init = subparsers.add_parser('init', help='Auto-generate .archit...; p_init.add_argument('path', nargs='?', default='.', help='Project root directory (default: cwd)'); p_init.add_argument('--force', action='store_true', help='Overwrite existing config file'); p_impact = subparsers.add_parser('impact', help='Impact analysis for...; p_impact.add_argument('model', help='Path to architecture-model.yaml'); p_impact.add_argument('entity_id', help='Entity ID to analyze'); p_impact.add_argument('--depth', type=int, default=2, help='Traversal depth'); p_manifest = subparsers.add_parser('manifest', help='Generate reality-...; p_manifest.add_argument('path', nargs='?', default='.', help='Project root directory (default: cwd)'); p_manifest.add_argument('-o', '--output', help='Output JSON path'); p_manifest.add_argument('--recursive', action='store_true', help='Generate per-F-block recursive manifests'); p_enrich = subparsers.add_parser('enrich', help='Auto-enrich model w...; p_enrich.add_argument('model', help='Path to architecture-model.yaml'); p_enrich.add_argument('--root', default='.', help='Project root directory'); p_decompose = subparsers.add_parser('decompose', help='Generate per-F-b...; p_decompose.add_argument('path', nargs='?', default='.', help='Project root directory (default: cwd)'); p_decompose.add_argument('-o', '--output', help='Output directory (default: .architecture-models/)'); p_coverage = subparsers.add_parser('coverage', help='Analyze model cov...; p_coverage.add_argument('model', help='Path to .architecture-model.yaml'); p_coverage.add_argument('--project', '-p', help='Project path for manifest generation (default: model directory)'); p_coverage.add_argument('--manifest', help='Path to pre-generated manifest JSON'); p_visualize = subparsers.add_parser('visualize', help='Generate Mermaid...; p_visualize.add_argument('path', nargs='?', default='.', help='Project root directory (default: cwd)'); p_visualize.add_argument('-o', '--output', default='output/diagrams', help='Output directory (default: output/diagrams)'); args = parser.parse_args(argv); if not args.command: ...; handlers = {'init': _cmd_init, 'validate': _cmd_validate, 'slice': _...; return handlers[args.command](args) |

## Patterns

None

## Confidence

0%


---

# Component: Orchestration (COMP-ORCHESTRATION)

**Status:** Status.ACTIVE
**Description:** Workflow orchestration — enrichment and decomposition pipelines

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/orchestration/decompose.py` | — | — |
| `src/architecture_model/orchestration/enrich.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| CAP-ENRICH | realizes | — |
| IF-ENRICH-MODEL | exposes | — |
| IF-DECOMPOSE-MODEL | exposes | — |
| COMP-CORE (Core) | depends-on | — |
| COMP-MANIFEST (Manifest) | depends-on | — |
| COMP-CONFIG (Config) | depends-on | — |
| LAYER-ORCH | allocated-to | — |

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| COMP-CLI (CLI) | depends-on | — |
| BEH-ENRICH-DECOMPOSE | traces-to | — |

## Behaviors Realized

None

## Public API

| Function | Parameters | Returns | Description |
|----------|-----------|---------|-------------|
| `decompose_model` | `project_root` | `` | model = load_model(project_root / '.architecture-model.yaml'); config = get_config(project_root); results = {}; for block_id, block_def in config.fblock_dict.items():
    block_name = block_def.get('name', block_id)
    block_dirs = block_def.get('dirs', [])
    block_files = block_def.get('files', [])
    logger.info('Decomposing %s: %s', block_id, block_name)
    components = _find_block_components(model, block_dirs, block_files)
    if not components:
        logger.warning('No components found for %s (dirs: %s)', block_id, block_dirs)
        continue
    parent_comp_id, parent_comp = _find_parent_component(model, components)
    comp_ids = {c.id for c in components}
    if parent_comp and parent_comp.id not in comp_ids:
        components = [parent_comp] + components
        comp_ids.add(parent_comp.id)
    block_comp_ids = comp_ids.copy()
    capabilities, interfaces, behaviors, constraints = _trace_entities(model, block_comp_ids)
    all_entity_ids = block_comp_ids.copy()
    all_entity_ids.update((c.id for c in capabilities))
    all_entity_ids.update((i.id for i in interfaces))
    all_entity_ids.update((b.id for b in behaviors))
    all_entity_ids.update((c.id for c in constraints))
    relationships = _collect_relationships(model, all_entity_ids, block_comp_ids)
    sub_model = ArchitectureModel(meta=ModelMeta(schema_version='2.0', project=f'{model.meta.project}/{block_name}', system=block_name, generated_at=model.meta.generated_at, parent_model='../../.architecture-model.yaml', refines_component=parent_comp_id or ''), entities=Entities(components=components, capabilities=capabilities, interfaces=interfaces, behaviors=behaviors, constraints=constraints), relationships=relationships)
    sub_behaviors_path = project_root / '.architecture-models' / 'sub-behaviors.yaml'
    _inject_sub_behaviors(sub_model, sub_behaviors_path)
    results[block_id] = sub_model
    logger.info('  %s: %d comps, %d caps, %d ifaces, %d behaviors, %d constraints, %d rels', block_id, len(components), len(capabilities), len(interfaces), len(behaviors), len(constraints), len(relationships)); return results |
| `write_sub_models` | `sub_models, output_dir` | `` | written = []; for block_id, model in sub_models.items():
    block_dir = output_dir / block_id
    block_dir.mkdir(parents=True, exist_ok=True)
    out_path = block_dir / '.architecture-model.yaml'
    save_model(model, out_path)
    written.append(out_path)
    logger.info('Wrote sub-model: %s', out_path); return written |
| `enrich_model` | `model: ArchitectureModel, project_root: Path` | `ArchitectureModel` | components = model.entities.get('components', []) if isinstance(model.entities, dict) else model.entities.components; for comp in components:
    if _enum_str(comp.status) != 'ACTIVE':
        continue
    if not comp.files:
        continue
    _enrich_signatures(comp, project_root)
    _enrich_constants(comp, project_root)
    _enrich_test_contracts(comp, project_root); return model |

## Patterns

None

## Confidence

0%


---

# Component: Extract (COMP-EXTRACT)

**Status:** Status.ACTIVE
**Description:** Model extraction from source code analysis

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/extract/from_code.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| CAP-EXTRACT | realizes | — |
| IF-EXTRACT-FROM-CODE | exposes | — |
| COMP-CORE (Core) | depends-on | — |
| COMP-CONFIG (Config) | depends-on | — |
| COMP-MANIFEST (Manifest) | depends-on | — |
| LAYER-ORCH | allocated-to | — |

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| BEH-EXTRACT | traces-to | — |

## Behaviors Realized

None

## Public API

| Function | Parameters | Returns | Description |
|----------|-----------|---------|-------------|
| `extract_from_code` | `project_root: str | Path, config: ProjectConfig | None, manifest: dict | None` | `ArchitectureModel` | root = Path(project_root).resolve(); if config is None: ...; if manifest is None: ...; capabilities = _derive_capabilities(config); routes = detect_routes(root, _get_web_layer_dirs(config)); actors = _derive_actors(routes, manifest); route_behaviors = _derive_route_behaviors(routes, config); service_behaviors = _detect_service_behaviors(root, config); behaviors = route_behaviors + service_behaviors; components = _derive_components(manifest, config); interfaces = _derive_interfaces(manifest, config); layers = _derive_layers(config); constraints = detect_constraints(root); entities = Entities(actors=actors, capabilities=capabilities, behavi...; relationships = _derive_relationships(capabilities=capabilities, behavior...; meta = ModelMeta(schema_version='1.0.0', project=config.name or ...; return ArchitectureModel(meta=meta, entities=entities, relationships=relationships) |

## Patterns

None

## Confidence

0%


---

# Component: Utils (COMP-UTILS)

**Status:** Status.ACTIVE
**Description:** Shared file discovery and exclusion patterns (72 lines)

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/utils/discovery.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| CAP-UTILS | realizes | — |
| IF-DISCOVER-FILES | exposes | — |
| LAYER-LIB | allocated-to | — |

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| COMP-CORE (Core) | depends-on | — |
| COMP-MANIFEST (Manifest) | depends-on | — |
| COMP-CONFIG (Config) | depends-on | — |

## Behaviors Realized

None

## Public API

| Function | Parameters | Returns | Description |
|----------|-----------|---------|-------------|
| `is_excluded_dir` | `path: Path` | `bool` | name = path.name; return name in EXCLUDED_DIRS or name.startswith('.') |
| `collect_py_files` | `directory: Path, recursive: bool, exclude_init: bool` | `list[Path]` | if not directory.is_dir():
    logger.debug('Directory does not exist: %s', directory)
    return []; glob_fn = directory.rglob if recursive else directory.glob; files = sorted((p for p in glob_fn('*.py') if not any((part in EXCLUDED_DIRS for part in p.parts)) and (not exclude_init or p.name != '__init__.py'))); logger.debug('Collected %d .py files from %s (recursive=%s)', len(files), directory, recursive); return files |
| `discover_source_files` | `project_root: Path` | `list[Path]` | all_py = collect_py_files(project_root, recursive=True); sources = [f for f in all_py if not _is_test_file(f, project_root)]; logger.info('Discovered %d source files (of %d total .py)', len(sources), len(all_py)); return sources |
| `discover_test_files` | `project_root: Path` | `list[Path]` | all_py = collect_py_files(project_root, recursive=True); tests = [f for f in all_py if _is_test_file(f, project_root)]; logger.info('Discovered %d test files', len(tests)); return tests |

## Patterns

None

## Confidence

0%


---

# Component: Profiles (COMP-PROFILES)

**Status:** Status.ACTIVE
**Description:** Domain profile loading — software, controls, mechanical, electrical (85 lines)

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/profiles/schema.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| CAP-PROFILES | realizes | — |
| IF-LOAD-PROFILE | exposes | — |
| LAYER-LIB | allocated-to | — |

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| COMP-CORE (Core) | depends-on | — |

## Behaviors Realized

None

## Public API

| Function | Parameters | Returns | Description |
|----------|-----------|---------|-------------|
| `from_dict` | `data: dict[str, Any]` | `DomainProfile` | return cls(domain=data['domain'], extends_schema=data.get('extends_schema', '1.4'), enum_extensions=[EnumExtension(**e) for e in data.get('enum_extensions', [])], entity_extensions=[EntityExtension(**e) for e in data.get('entity_extensions', [])], validation_rules=[ConditionalRule(**r) for r in data.get('validation_rules', [])]) |
| `get_extended_values` | `enum_name: str` | `list[str]` | for ext in self.enum_extensions:
    if ext.enum_name == enum_name:
        return ext.values; return [] |
| `load_profile` | `name_or_path: str` | `DomainProfile` | if name_or_path in BUILTIN_PROFILES: ...; if not path.exists(): ...; data = yaml.safe_load(path.read_text(encoding='utf-8')); profile = DomainProfile.from_dict(data); logger.info('Loaded domain profile: %s', profile.domain); return profile |
| `DomainProfile.from_dict` | `data: dict[str, Any]` | `DomainProfile` | return cls(domain=data['domain'], extends_schema=data.get('extends_schema', '1.4'), enum_extensions=[EnumExtension(**e) for e in data.get('enum_extensions', [])], entity_extensions=[EntityExtension(**e) for e in data.get('entity_extensions', [])], validation_rules=[ConditionalRule(**r) for r in data.get('validation_rules', [])]) |
| `DomainProfile.get_extended_values` | `enum_name: str` | `list[str]` | for ext in self.enum_extensions:
    if ext.enum_name == enum_name:
        return ext.values; return [] |

## Patterns

None

## Confidence

0%


---

# Component: Spec (COMP-SPEC)

**Status:** Status.ACTIVE
**Description:** JSON Schema definitions for model validation (data only, no code)

## Files

None

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| CAP-SCHEMA | realizes | — |
| LAYER-LIB | allocated-to | — |

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| COMP-CORE (Core) | depends-on | — |

## Behaviors Realized

None

## Patterns

None

## Confidence

0%
