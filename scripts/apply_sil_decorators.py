#!/usr/bin/env python
"""SI&L decorator coverage checker (Plan B DoD step 6).

Verifies that every architecturally significant call site declared by
Plan B (2026-09-05-sil-and-provider) still carries an ``@instrumented(...)``
decorator with the expected component_id. The decorator sets two attributes
on the wrapped callable — ``__sil_instrumented__`` and
``__sil_component_id__`` — which this script asserts.

Usage:
    python scripts/apply_sil_decorators.py --check      # exit 1 on any miss
    python scripts/apply_sil_decorators.py              # verbose report

Coverage:
    * 10 pipeline stages       (stage:*)
    * 6 lifecycle renderers    (renderer:*)  incl. pipeline-html
    * 3 validators             (validator:*)

The 19 OCA MCP tool decorators (``mcp_tool:*``) live in the sibling
repo and are covered by OCA's own parametrized instrumentation tests
(``tests/test_instrumentation.py``); this script deliberately does not
reach across repos.
"""
from __future__ import annotations

import argparse
import importlib
import sys
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Site:
    """One expected instrumented call site."""

    dotted_path: str  # "package.module:Class.method" or "package.module:function"
    component_id: str


# ---------------------------------------------------------------------------
# Expected coverage (single source of truth for Plan B B2.2.1–B2.2.3)
# ---------------------------------------------------------------------------
EXPECTED: tuple[Site, ...] = (
    # --- 10 pipeline stages ---
    Site("architecture_model.pipeline.observe:ObserveStage.run", "stage:observe"),
    Site("architecture_model.pipeline.infer:InferStage.run", "stage:infer"),
    Site("architecture_model.pipeline.allocate:AllocateStage.run", "stage:allocate"),
    Site("architecture_model.pipeline.relate:RelateStage.run", "stage:relate"),
    Site("architecture_model.pipeline.specify:SpecifyStage.run", "stage:specify"),
    Site("architecture_model.pipeline.contract:ContractStage.run", "stage:contract"),
    Site("architecture_model.pipeline.validate:ValidateStage.run", "stage:validate"),
    Site("architecture_model.pipeline.decompose:DecomposeStage.run", "stage:decompose"),
    Site("architecture_model.pipeline.synthesize:SynthesizeStage.run", "stage:synthesize"),
    Site("architecture_model.pipeline.emit:EmitStage.run", "stage:emit"),
    # --- 6 lifecycle renderers ---
    Site("architecture_model.lifecycle.renderers.svg:render_svg", "renderer:svg"),
    Site("architecture_model.lifecycle.renderers.markdown:render_markdown", "renderer:markdown"),
    Site("architecture_model.lifecycle.renderers.html:render_html", "renderer:html"),
    Site("architecture_model.lifecycle.renderers.ai_context:render_ai_context", "renderer:ai-context"),
    Site("architecture_model.lifecycle.renderers.zip:render_zip", "renderer:zip"),
    Site("architecture_model.lifecycle.renderers.pipeline_html:render_pipeline_html", "renderer:pipeline-html"),
    # --- 3 validators ---
    Site("architecture_model.core.validator:validate_model", "validator:validate"),
    Site("architecture_model.core.representativeness:compute_representativeness", "validator:check"),
    Site("architecture_model.authoring.gate:check_development_gate", "validator:gate"),
)


def _resolve(dotted: str) -> Callable:
    """Resolve ``module.path:Class.method`` or ``module.path:function``."""
    module_path, _, attr_path = dotted.partition(":")
    if not attr_path:
        raise ValueError(f"missing ':' in {dotted!r}")
    mod = importlib.import_module(module_path)
    obj = mod
    for part in attr_path.split("."):
        obj = getattr(obj, part)
    return obj


def check_site(site: Site) -> tuple[bool, str]:
    """Return (ok, detail) — detail describes the reason on failure."""
    try:
        fn = _resolve(site.dotted_path)
    except (ImportError, AttributeError, ValueError) as e:
        return False, f"resolve failed: {type(e).__name__}: {e}"

    if not getattr(fn, "__sil_instrumented__", False):
        return False, "missing @instrumented decorator"

    actual = getattr(fn, "__sil_component_id__", None)
    if actual != site.component_id:
        return False, f"component_id mismatch: expected {site.component_id!r}, got {actual!r}"

    return True, site.component_id


def run(*, check_mode: bool) -> int:
    misses: list[tuple[Site, str]] = []
    hits: list[Site] = []
    for site in EXPECTED:
        ok, detail = check_site(site)
        if ok:
            hits.append(site)
            if not check_mode:
                print(f"OK    {site.dotted_path:70s} {site.component_id}")
        else:
            misses.append((site, detail))
            print(f"MISS  {site.dotted_path:70s} {detail}", file=sys.stderr)

    total = len(EXPECTED)
    if not check_mode:
        print(f"\nSummary: {len(hits)}/{total} instrumented sites present.")

    if misses:
        print(f"\n{len(misses)} miss(es) detected.", file=sys.stderr)
        return 1
    if check_mode:
        print(f"All {total} SI&L instrumentation sites present.")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="SI&L decorator coverage checker")
    p.add_argument(
        "--check",
        action="store_true",
        help="Terse pass/fail mode (exit 1 on any missing decorator).",
    )
    args = p.parse_args()
    return run(check_mode=args.check)


if __name__ == "__main__":
    sys.exit(main())
