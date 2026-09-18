# Graph Export (Stage 1)

Export the AMS v3 architecture model as a NetworkX
[`MultiDiGraph`](https://networkx.org/documentation/stable/reference/classes/multidigraph.html)
for use in graph analysis tools (yEd, Gephi, Cytoscape.js, Neo4j import,
custom Python analytics).

**Status:** Stage 1 — export-only. Walks/traverse are unchanged. YAML
remains source of truth; the graph is a derived, rebuildable view.

## Install

```bash
pip install 'architecture-model-standard[graph]'          # networkx
pip install 'architecture-model-standard[graph-dot]'      # + pydot for .dot
```

## CLI

```
architecture-model export-graph [MODEL_PATH]
  -f, --format {graphml,gpickle,json-graph,dot}   # default: graphml
  -o, --output PATH                                # default: ./model.<ext>
  --no-promises                                    # skip promise/evidence promotion
  --no-semantic                                    # skip semantic bag on nodes
  --stats                                          # print counts, do not write
```

MODEL_PATH defaults to `.architecture-model.v3.yaml`, falling back to
`.architecture-model.yaml`.

### Examples

```bash
architecture-model export-graph --stats
# nodes: 1011
# edges: 1086
# by-node-kind: capability: 17, component: 25, promise: 802, evidence: 132, ...
# by-edge-type: has-promise: 802, verified-by: 133, depends-on: 54, ...

architecture-model export-graph -f graphml -o /tmp/ams.graphml
# Open /tmp/ams.graphml in yEd or Gephi.

architecture-model export-graph -f json-graph -o /tmp/ams.json
# For Cytoscape.js / d3-force / custom JS viewers.

architecture-model export-graph --no-promises -f gpickle -o /tmp/ams.pkl
# Structural-only subgraph (entities + canonical relationships).
```

## Format matrix

| Format | Extension | Primary use | Notes |
|---|---|---|---|
| `graphml` | `.graphml` | yEd, Gephi, Cytoscape | Portable XML; list/dict attrs are JSON-stringified |
| `gpickle` | `.gpickle` | Round-trip Python | Preserves all attr types |
| `json-graph` | `.json` | JS viewers, LLM prompts | node-link format |
| `dot` | `.dot` | Graphviz | Requires `pydot` (`graph-dot` extra) |

## Python API

```python
from architecture_model.core.v3_loader import load_v3_model
from architecture_model.graph import to_networkx

model = load_v3_model()
G = to_networkx(
    model,
    promises_as_nodes=True,       # promote promises → sub-nodes
    include_verified_by=True,     # promote evidence URIs → nodes
    include_semantic_fields=True, # carry intent/goals/owner/... on nodes
)

# G is a networkx.MultiDiGraph — parallel typed edges preserved.
print(G.number_of_nodes(), G.number_of_edges())
```

## Node schema

| Kind | ID format | Attrs |
|---|---|---|
| Entity | entity `id` (e.g. `CAP-A`, `COMP-1`) | `kind`, `bucket`, `name`, `status`, + semantic bag |
| Promise | `{owner_id}#p{index}` (e.g. `CAP-A#p0`) | `kind="promise"`, `owner_id`, `promise_index`, `promise_id`, `attr`, `value`, `status`, `confidence` |
| Evidence | `ev:{sha1(uri)[:8]}` | `kind="evidence"`, `uri`, `evidence_kind` |

## Edge schema

Edge **key** = relationship type. This is deliberate: parallel typed
edges (same `(u, v)`, different type) are preserved as distinct edges.

**Canonical types (17):** `realizes`, `contains`, `depends-on`,
`constrained-by`, `traces-to`, `exposes`, `consumes`, `triggers`,
`allocated-to`, `produces`, `subscribes-to`, `transforms`, `supersedes`,
`migrates-to`, `mounted-on`, `connected-at`, `routed-through`.

**Synthetic types (2):** `has-promise` (entity → promise),
`verified-by` (promise → evidence).

Extra relationship attrs (`weight`, `note`, `direction`, …) are
propagated verbatim onto edge data.

## Determinism

Two calls to `to_networkx()` on the same model produce identical node
and edge iteration order. Determinism is test-enforced
(`test_determinism_two_builds_identical_ordering`).

Ordering rules:
1. Buckets in fixed order (`capabilities, components, behaviors,
   interfaces, actors, constraints, layers, environments, resources`)
2. Entities sorted by `id` within bucket
3. Promises in YAML list order (index-stable)
4. Evidence dedup by URI, first-seen wins
5. Relationships sorted by `(from, to, type)` before insertion

## Out of scope (Stage 2+)

- Walk-backend swap (traverse.py using nx internally)
- Neo4j adapter + Cypher query surface
- Compliance-evidence walk
