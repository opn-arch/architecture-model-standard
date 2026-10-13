"""pipeline_v3 — Promise-graph-native extraction pipeline (T0.14 Phase 6).

Eight-stage pipeline consuming a repo and producing a v3 architecture
model (Promise-graph + entities + relationships):

    scan -> derive_promises -> cluster -> link -> containerize
         -> verify -> publish
    (orchestrated by orchestrator)

Each stage is a self-contained module with its own tests. Intermediate
data types flow between stages via typed dataclasses; no stage reaches
back into a previous stage's internals.
"""
