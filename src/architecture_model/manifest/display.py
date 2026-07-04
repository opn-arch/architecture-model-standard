"""Terminal summary display for the reality manifest."""

from __future__ import annotations

from typing import Any


def print_summary(manifest: dict[str, Any]) -> None:
    """Print a terminal summary of the manifest."""
    metrics = manifest["metrics"]
    blocks = manifest["functional_blocks"]

    print(f"\n{'=' * 60}")
    print("REALITY MANIFEST SUMMARY")
    print(f"{'=' * 60}")
    print(f"  Generated: {manifest['generated_at']}")
    print(f"  Root:      {manifest['project_root']}")
    print()
    print("  METRICS:")
    # Show all available metrics dynamically
    known_labels = ["router", "model", "migration", "template"]
    shown = False
    for label in known_labels:
        key = f"{label}_count"
        if key in metrics:
            print(f"    {label.title() + 's:':<14}{metrics[key]}")
            shown = True
    # Show any additional metrics not in known list
    for key, val in metrics.items():
        if key == "total_python_files":
            continue
        if key.endswith("_count") and key.replace("_count", "") not in known_labels:
            label = key.replace("_count", "").replace("_", " ").title()
            print(f"    {label + ':':<14}{val}")
            shown = True
    if not shown:
        print(f"    (no standard metrics detected)")
    print(f"    Python files: {metrics.get('total_python_files', 'N/A')}")
    print()
    print("  FUNCTIONAL BLOCKS:")
    for block_id, block in blocks.items():
        sf_count = len(block.get("sub_functions", []))
        active = sum(1 for sf in block.get("sub_functions", []) if sf["status"] == "active")
        print(
            f"    {block_id}: {block['name']:<30} [{block['status']:>7}] "
            f"({active}/{sf_count} active)"
        )
    print()
    print(f"  INTERFACES: {len(manifest.get('interfaces', []))} dependencies detected")
    print(f"  MODULES:    {len(manifest.get('modules', []))} files scanned")
    print(f"{'=' * 60}")
