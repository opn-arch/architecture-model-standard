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
    print(f"    Routers:      {metrics['router_count']}")
    print(f"    Models:       {metrics['model_count']}")
    print(f"    Migrations:   {metrics['migration_count']}")
    print(f"    Templates:    {metrics['template_count']}")
    print(f"    Python files: {metrics['total_python_files']}")
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
