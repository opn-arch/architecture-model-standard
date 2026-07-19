#!/usr/bin/env python3
"""Strip sub-behaviors from parent model into separate sub-behaviors.yaml file.

Moves 70 sub-behaviors out of the parent model, keeping only the 9 top-level
parent behaviors. Sub-behaviors are saved to .architecture-models/sub-behaviors.yaml
for injection into sub-models during decomposition.
"""
from pathlib import Path
import yaml

from architecture_model.core.parser import load_model, save_model, _dump_behavior

PARENT_BEHAVIOR_IDS = {
    "BEH-INIT", "BEH-VALIDATE", "BEH-MANIFEST", "BEH-ENRICH",
    "BEH-EXTRACT", "BEH-SLICE", "BEH-DIFF", "BEH-MERGE", "BEH-DECOMPOSE",
}


def main():
    project_root = Path(".")
    model_path = project_root / ".architecture-model.yaml"
    model = load_model(model_path)

    # Identify sub-behaviors
    parent_behs = [b for b in model.entities.behaviors if b.id in PARENT_BEHAVIOR_IDS]
    sub_behs = [b for b in model.entities.behaviors if b.id not in PARENT_BEHAVIOR_IDS]

    print(f"Parent behaviors to keep: {len(parent_behs)}")
    print(f"Sub-behaviors to strip: {len(sub_behs)}")

    sub_beh_ids = {b.id for b in sub_behs}

    # Build lookup: sub_behavior_id -> parent_behavior (from contains rels)
    # Build lookup: sub_behavior_id -> component (from traces-to rels)
    parent_map = {}
    component_map = {}

    rels_to_remove = []
    rels_to_keep = []

    for rel in model.relationships:
        remove = False

        # contains from parent behavior to sub-behavior
        if rel.type.value == "contains" and rel.from_id in PARENT_BEHAVIOR_IDS and rel.to_id in sub_beh_ids:
            parent_map[rel.to_id] = rel.from_id
            remove = True

        # traces-to to a sub-behavior
        elif rel.type.value == "traces-to" and rel.to_id in sub_beh_ids:
            component_map[rel.to_id] = rel.from_id
            remove = True

        if remove:
            rels_to_remove.append(rel)
        else:
            rels_to_keep.append(rel)

    print(f"Relationships to remove: {len(rels_to_remove)}")
    print(f"Relationships to keep: {len(rels_to_keep)}")

    # Build sub-behaviors.yaml entries
    sub_entries = []
    for b in sub_behs:
        entry = _dump_behavior(b)
        entry["parent_behavior"] = parent_map.get(b.id, "")
        entry["component"] = component_map.get(b.id, "")
        sub_entries.append(entry)

    # Save sub-behaviors.yaml
    out_dir = project_root / ".architecture-models"
    out_dir.mkdir(parents=True, exist_ok=True)
    sub_path = out_dir / "sub-behaviors.yaml"
    with open(sub_path, "w") as f:
        f.write("# Sub-behaviors for injection into sub-models during decomposition\n")
        yaml.dump(
            {"behaviors": sub_entries},
            f, default_flow_style=False, sort_keys=False, allow_unicode=True, width=120,
        )
    print(f"Saved {len(sub_entries)} sub-behaviors to {sub_path}")

    # Strip parent model
    model.entities.behaviors = parent_behs
    model.relationships = rels_to_keep

    save_model(model, model_path)
    print(f"Saved stripped parent model to {model_path}")
    print(f"Parent model now has {len(parent_behs)} behaviors, {len(rels_to_keep)} relationships")


if __name__ == "__main__":
    main()
