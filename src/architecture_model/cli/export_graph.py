"""architecture-model export-graph — NetworkX graph exporter CLI.

Exports the merged v3 model as a NetworkX MultiDiGraph in one of several
serialization formats, or prints structural stats without writing.

Usage::

    architecture-model export-graph [MODEL_PATH]
      -f, --format {graphml,gpickle,json-graph,dot}   (default: graphml)
      -o, --output PATH
      --no-promises
      --no-semantic
      --stats
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

FORMATS = ("graphml", "gpickle", "json-graph", "dot")
_EXT = {
    "graphml": ".graphml",
    "gpickle": ".gpickle",
    "json-graph": ".json",
    "dot": ".dot",
}


def add_subparser(subparsers) -> argparse.ArgumentParser:
    """Register the export-graph subcommand."""
    p = subparsers.add_parser(
        "export-graph",
        help="Export model as NetworkX graph (graphml/gpickle/json-graph/dot)",
    )
    p.add_argument(
        "model_path",
        nargs="?",
        default=None,
        help="Path to model YAML (default: .architecture-model.v3.yaml)",
    )
    p.add_argument(
        "-f",
        "--format",
        choices=FORMATS,
        default="graphml",
        help="Output format (default: graphml)",
    )
    p.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output path (default: ./model.<ext>)",
    )
    p.add_argument(
        "--no-promises",
        action="store_true",
        help="Skip promise/evidence promotion",
    )
    p.add_argument(
        "--no-semantic",
        action="store_true",
        help="Skip semantic bag on entity nodes",
    )
    p.add_argument(
        "--stats",
        action="store_true",
        help="Print node/edge counts; do not write output",
    )
    p.set_defaults(func=run)
    return p


def _write_graph(G, fmt: str, out_path: Path) -> None:
    import networkx as nx

    if fmt == "graphml":
        # graphml cannot serialize non-primitive values; coerce complex attrs to str.
        _coerce_for_graphml(G)
        nx.write_graphml(G, str(out_path))
    elif fmt == "gpickle":
        # nx dropped write_gpickle in 3.x; use pickle directly.
        import pickle

        with open(out_path, "wb") as fh:
            pickle.dump(G, fh)
    elif fmt == "json-graph":
        data = nx.node_link_data(G, edges="edges")
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, sort_keys=True, default=str)
    elif fmt == "dot":
        try:
            from networkx.drawing.nx_pydot import write_dot
        except ImportError as exc:
            raise ImportError(
                "pydot is required for dot format. Install with:\n"
                "  pip install 'architecture-model-standard[graph-dot]'"
            ) from exc
        write_dot(G, str(out_path))
    else:  # pragma: no cover
        raise ValueError(f"Unknown format: {fmt}")


def _coerce_for_graphml(G) -> None:
    """Coerce list/dict node & edge attrs to strings for graphml compatibility."""
    for _, data in G.nodes(data=True):
        for k, v in list(data.items()):
            if isinstance(v, (list, dict, tuple, set)):
                data[k] = json.dumps(v, sort_keys=True, default=str)
            elif v is None:
                data[k] = ""
    for _, _, data in G.edges(data=True):
        for k, v in list(data.items()):
            if isinstance(v, (list, dict, tuple, set)):
                data[k] = json.dumps(v, sort_keys=True, default=str)
            elif v is None:
                data[k] = ""


def _print_stats(G) -> None:
    node_kinds = Counter(d.get("kind", "?") for _, d in G.nodes(data=True))
    edge_types = Counter(d.get("type", "?") for _, _, d in G.edges(data=True))
    print(f"nodes: {G.number_of_nodes()}")
    print(f"edges: {G.number_of_edges()}")
    print("by-node-kind:")
    for k in sorted(node_kinds):
        print(f"  {k}: {node_kinds[k]}")
    print("by-edge-type:")
    for t in sorted(edge_types):
        print(f"  {t}: {edge_types[t]}")


def run(args: argparse.Namespace) -> int:
    from architecture_model.core.v3_loader import load_v3_model
    from architecture_model.graph import to_networkx

    model_path = Path(args.model_path) if args.model_path else None
    try:
        model = load_v3_model(model_path=model_path)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    try:
        G = to_networkx(
            model,
            promises_as_nodes=not args.no_promises,
            include_verified_by=not args.no_promises,
            include_semantic_fields=not args.no_semantic,
        )
    except ImportError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 4

    if args.stats:
        _print_stats(G)
        return 0

    fmt = args.format
    if args.output:
        out_path = Path(args.output)
    else:
        out_path = Path.cwd() / f"model{_EXT[fmt]}"

    try:
        _write_graph(G, fmt, out_path)
    except ImportError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 4

    print(
        f"wrote {out_path} "
        f"({G.number_of_nodes()} nodes, {G.number_of_edges()} edges)"
    )
    return 0
