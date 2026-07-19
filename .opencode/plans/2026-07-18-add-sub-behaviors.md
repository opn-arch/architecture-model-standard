# Add Function-Level Sub-Behaviors Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add ~69 function-level sub-behavior entities to the architecture model, making sub-models useful for code regeneration by describing algorithmic workflows at block level.

**Architecture:** A Python script (`scripts/add_sub_behaviors.py`) loads the model via `load_model()`, appends Behavior entities + Relationship objects, saves via `save_model()`. Sub-behaviors use `contains` relationships from parent behaviors and `traces-to` from implementing components. The decomposer already picks up behaviors via `traces-to` — no code changes needed.

**Tech Stack:** Python, architecture_model.core.parser, architecture_model.core.types

---

### Task 1: Write the sub-behavior addition script

**Files:**
- Create: `scripts/add_sub_behaviors.py`

**Step 1: Write the script**

The script must:
1. Load model from `.architecture-model.yaml`
2. Define all sub-behaviors as tuples (id, name, description, parent_behavior_id, component_id, steps)
3. Create Behavior dataclass instances + Relationship objects (contains + traces-to)
4. Deduplicate: skip any behavior ID that already exists (idempotent)
5. Verify all component IDs exist before adding
6. Save model back via save_model()

**Sub-behavior definitions (65 sub-behaviors + 4 new parents = 69 total):**

New parent behaviors (no parent themselves):
- BEH-SLICE: "Model Slicing" — component COMP-CLI traces-to
- BEH-DIFF: "Model Diffing" — component COMP-CLI traces-to  
- BEH-MERGE: "Model Merging" — component COMP-CORE-MERGER traces-to
- BEH-DECOMPOSE: "Model Decomposition" — component COMP-CLI traces-to

**F3 Core — Validator** (parent: BEH-VALIDATE, component: COMP-CORE-VALIDATOR)

| ID | Name | Steps |
|----|------|-------|
| BEH-VALIDATE-IDS | ID Uniqueness Check | Collect all entity IDs → Detect duplicates → ERROR per duplicate |
| BEH-VALIDATE-REFS | Referential Integrity Check | Collect entity IDs → Check relationship from/to → ERROR per dangling |
| BEH-VALIDATE-ORPHANS | Orphan Entity Detection | Build adjacency set → Check each entity → WARNING per orphan |
| BEH-VALIDATE-STATUS | Status Consistency Check | Check each entity status → ERROR for invalid |
| BEH-VALIDATE-CAPS | Capability Realization Check | Collect cap IDs → Check realizes rels → WARNING per unrealized |
| BEH-VALIDATE-META | Meta Completeness Check | Check project name → Check schema_version → ERROR per missing |
| BEH-VALIDATE-V11 | V1.1 Semantics Check | Check component kinds → Check interface types → Validate rel types |
| BEH-VALIDATE-REGEN | Regen Readiness Check | Check signatures → Check test_contracts → Check constants → ERROR per missing |
| BEH-VALIDATE-PROFILE | Domain Profile Validation | Load profile → Apply validators → Report violations |
| BEH-VALIDATE-IMPROVE | Improvement Opportunities | Check descriptions → Check tags → INFO suggestions |

**F3 Core — Parser** (parent: BEH-VALIDATE, component: COMP-CORE-PARSER)

| ID | Name |
|----|------|
| BEH-PARSE-LOAD | Model Loading |
| BEH-PARSE-SAVE | Model Saving |
| BEH-PARSE-DUMP | Model Dumping |

**F3 Core — Slicer** (parent: BEH-SLICE, component: COMP-CORE-SLICER)

| ID | Name |
|----|------|
| BEH-SLICE-FBLOCK | Slice by F-Block |
| BEH-SLICE-LAYER | Slice by Layer |
| BEH-SLICE-STATUS | Slice by Status |
| BEH-SLICE-ARTIFACT | Slice by Artifact |
| BEH-SLICE-COMPONENT | Slice by Component |

**F3 Core — Differ** (parent: BEH-DIFF, component: COMP-CORE-DIFFER)

| ID | Name |
|----|------|
| BEH-DIFF-ENTITIES | Entity Diff |
| BEH-DIFF-RELS | Relationship Diff |

**F3 Core — Merger** (parent: BEH-MERGE, component: COMP-CORE-MERGER)

| ID | Name |
|----|------|
| BEH-MERGE-MANIFEST | Merge Manifest |
| BEH-MERGE-ENRICH | Enrich from Manifest |
| BEH-MERGE-COMPACT | Compact for Generation |
| BEH-MERGE-COMPOSE | Compose Enriched Model |

**F3 Core — Decomposer** (parent: BEH-DECOMPOSE, component: COMP-DECOMPOSE)

| ID | Name |
|----|------|
| BEH-DECOMPOSE-IDENTIFY | Identify Systems |
| BEH-DECOMPOSE-COMPLEXITY | Compute Complexity |
| BEH-DECOMPOSE-PARTITION | Partition Subsystems |

**F5 Manifest — Scanner** (parent: BEH-MANIFEST, component: COMP-MANIFEST-SCANNER)

| ID | Name |
|----|------|
| BEH-SCAN-PARSE | AST Parsing |
| BEH-SCAN-FUNCTIONS | Function Extraction |
| BEH-SCAN-CLASSES | Class Extraction |
| BEH-SCAN-IMPORTS | Import Extraction |
| BEH-SCAN-CONSTANTS | Constant Extraction |
| BEH-SCAN-METRICS | Metrics Computation |

**F5 Manifest — Generator** (parent: BEH-MANIFEST, component: COMP-MANIFEST-GENERATOR)

| ID | Name |
|----|------|
| BEH-MANIFEST-CONFIG | Config Loading |
| BEH-MANIFEST-METRICS | Project Metrics |
| BEH-MANIFEST-BLOCKS | Block Assembly |
| BEH-MANIFEST-SCAN | Block Scanning |
| BEH-MANIFEST-IFACE | Interface Discovery |
| BEH-MANIFEST-ASSEMBLE | Manifest Assembly |

**F5 Manifest — Body Hints** (parent: BEH-MANIFEST, component: COMP-MANIFEST-BODYHINTS)

| ID | Name |
|----|------|
| BEH-BODYHINT-CLASSIFY | Complexity Classification |
| BEH-BODYHINT-SUMMARIZE | Body Summarization |

**F5 Manifest — Test Analyzer** (parent: BEH-MANIFEST, component: COMP-MANIFEST-TESTANALYZER)

| ID | Name |
|----|------|
| BEH-TEST-DISCOVER | Test Method Discovery |
| BEH-TEST-ASSERTIONS | Assertion Pattern Matching |

**F5 Manifest — Interfaces** (parent: BEH-MANIFEST, component: COMP-MANIFEST-INTERFACES)

| ID | Name |
|----|------|
| BEH-IFACE-RESOLVE | Import Resolution |
| BEH-IFACE-DEDUP | Interface Deduplication |

**F5 Manifest — Recursive** (parent: BEH-MANIFEST, component: COMP-MANIFEST-RECURSIVE)

| ID | Name |
|----|------|
| BEH-RECURSIVE-SCAN | Per-Block Deep Scan |
| BEH-RECURSIVE-DEPS | Cross-Block Dependencies |

**F6 Orchestration — Enrich** (parent: BEH-ENRICH, component: COMP-ENRICH)

| ID | Name |
|----|------|
| BEH-ENRICH-SIGS | Signature Enrichment |
| BEH-ENRICH-CONSTS | Constant Enrichment |
| BEH-ENRICH-TESTS | Test Contract Enrichment |

**F6 Orchestration — Decompose** (parent: BEH-ENRICH, component: COMP-ORCH-DECOMPOSE — verify actual ID)

| ID | Name |
|----|------|
| BEH-ORCH-FIND-COMPS | Find Block Components |
| BEH-ORCH-FIND-PARENT | Find Parent Component |
| BEH-ORCH-TRACE | Trace Entities |
| BEH-ORCH-COLLECT-RELS | Collect Relationships |
| BEH-ORCH-BUILD | Build Sub-Model |

**F4 Extract** (parent: BEH-EXTRACT, component: COMP-EXTRACT)

| ID | Name |
|----|------|
| BEH-EXTRACT-CAPS | Extract Capabilities |
| BEH-EXTRACT-ACTORS | Extract Actors |
| BEH-EXTRACT-COMPS | Extract Components |
| BEH-EXTRACT-IFACES | Extract Interfaces |
| BEH-EXTRACT-RELS | Extract Relationships |

**F1 CLI** (parent: BEH-INIT, component: COMP-CLI)

| ID | Name |
|----|------|
| BEH-CLI-SLICE | CLI Slice Command |
| BEH-CLI-DIFF | CLI Diff Command |
| BEH-CLI-STATS | CLI Stats Command |
| BEH-CLI-IMPACT | CLI Impact Command |
| BEH-CLI-DECOMPOSE | CLI Decompose Command |
| BEH-CLI-COVERAGE | CLI Coverage Command |

**F7 Profiles** (parent: BEH-VALIDATE, component: COMP-PROFILES)

| ID | Name |
|----|------|
| BEH-PROFILE-LOAD | Load Profile |
| BEH-PROFILE-APPLY | Apply Profile Rules |

**F9 Utils** (parent: BEH-MANIFEST, component: COMP-UTILS)

| ID | Name |
|----|------|
| BEH-UTILS-DISCOVER | File Discovery |
| BEH-UTILS-TESTS | Test File Discovery |

**Script skeleton** (see Task 1 description above for full structure):

```python
#!/usr/bin/env python3
"""Add function-level sub-behaviors to the architecture model.

Idempotent: skips behaviors that already exist.
"""
from pathlib import Path
from architecture_model.core.parser import load_model, save_model
from architecture_model.core.types import (
    Behavior, BehaviorPattern, Relationship, RelationType, Status, Priority,
)

MODEL_PATH = Path(".architecture-model.yaml")

# Define all sub-behaviors as: (id, name, desc, parent_id, component_id, steps)
# ... all 65 entries from tables above ...

def main():
    model = load_model(MODEL_PATH)
    existing_ids = {b.id for b in model.entities.behaviors}
    comp_ids = {c.id for c in model.entities.components}
    
    # Verify component IDs
    for entry in SUB_BEHAVIORS:
        comp_id = entry[4]
        assert comp_id in comp_ids, f"Component {comp_id} not found (for {entry[0]})"
    
    # Add parent behaviors, then sub-behaviors
    # Add contains + traces-to relationships
    # Deduplicate
    
    save_model(model, MODEL_PATH)
```

**IMPORTANT:** Before writing the script, run this to get exact component IDs:

```bash
python3 -c "
from architecture_model.core.parser import load_model
m = load_model('.architecture-model.yaml')
for c in m.entities.components:
    print(f'{c.id}: {c.name} (f_block={getattr(c, \"f_block\", \"?\")})')
"
```

**Step 2: Run the script**

```bash
python scripts/add_sub_behaviors.py
```

Expected: "Added 69 sub-behaviors" and ~230 total relationships.

**Step 3: Commit**

```bash
git add scripts/add_sub_behaviors.py .architecture-model.yaml
git commit -m "feat: add 69 function-level sub-behaviors to architecture model"
```

---

### Task 2: Validate the enriched model

**Step 1: Run validation**

```bash
python -m architecture_model.cli.main validate .
```

Expected: 100/100.

**Step 2: Run existing tests**

```bash
pytest tests/ -v --ignore=tests/test_config_loader.py --ignore=tests/test_coverage.py
```

Expected: 453+ pass, 0 fail.

**Step 3: Fix any issues and commit if needed**

---

### Task 3: Regenerate sub-models

**Step 1: Run decompose**

```bash
python -m architecture_model.cli.main decompose .
```

**Step 2: Verify sub-models contain block-specific sub-behaviors**

```bash
python3 -c "
from architecture_model.core.parser import load_model
for i in range(1, 10):
    m = load_model(f'.architecture-models/F{i}/model.yaml')
    behs = [b.id for b in m.entities.behaviors]
    print(f'F{i}: {len(behs)} behaviors: {behs}')
"
```

Expected: F3 ~27 behaviors, F5 ~18, F6 ~8, etc.

**Step 3: Commit**

```bash
git add .architecture-models/
git commit -m "chore: regenerate sub-models with function-level sub-behaviors"
```

---

### Task 4: Regenerate reference docs and PDFs

**Step 1: Regenerate**

```bash
python scripts/generate_models_pdf.py
```

**Step 2: Commit**

```bash
git add output/
git commit -m "chore: regenerate reference docs with sub-behaviors"
```

---

### Task 5: Update CONTEXT.md

Update behavior count (5 → 74), relationship count (93 → ~230).

```bash
git add CONTEXT.md
git commit -m "docs: update CONTEXT.md with sub-behavior counts"
```

---

## Verification Checklist

- [ ] 69 new behaviors added (4 parent + 65 sub)
- [ ] Every sub-behavior has `contains` from parent + `traces-to` from component
- [ ] Validation score: 100/100
- [ ] All existing tests pass (453+)
- [ ] Each sub-model (F1-F9) contains its block-specific sub-behaviors
- [ ] PDFs regenerated
- [ ] CONTEXT.md updated
