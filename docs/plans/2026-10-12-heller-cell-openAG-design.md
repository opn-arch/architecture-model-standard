# Design: openAG Heller Cell — Semantic Digital-Twin Model (validation-driven)

**Status:** Approved design — ready for implementation. Design-only artifacts;
no engine code. openAG remains **zero-code** and AMS **frozen until parity** —
the standard extensions below are **documentation + schema** only.

**Date:** 2026-10-12. **Owner:** (modeler). **First openAG reference model.**

---

## 1. Goals and scope

Two goals, pursued by the same artifact:

- **G1 — Validate / advance openAG.** The Heller Cell is a real, hard,
  multi-disciplinary cyber-physical system. Authoring it by hand against the
  openAG standard is the best possible forcing function: every place the
  standard strains is a recorded finding (`FINDINGS.md`).
- **G2 — A model that can capture the *entire* Heller cell** as a
  digital-twin backbone (single source of truth): structure, all
  disciplines, geometry references, kinematics, and live-data binding points.

**The model is the deliverable.** Presentation / projection is a **separate,
downstream concern** and is explicitly **out of scope** for this work:

- NOT building a 3D renderer.
- NOT acquiring CAD / meshes.
- NOT running physics or kinematics.
- NOT wiring live SCADA/OPC-UA data.

The model must be *capable* of representing all of the above (it carries
geometry **references**, kinematic **descriptors**, and live-binding
**descriptors** — never heavy payloads). Rendering, simulation, and live
binding consume this model later, separately.

### 1.1 The target system

The Heller Cell: five Heller CNC machines (each with an automatic tool
changer), fed with parts from a part store and tools from a tool store via
two robots, plus a coolant system. Control is distributed across multiple
PLCs with robot programs and comms; a supervisory layer provides SCADA,
servers, and databases.

---

## 2. Approach: the model IS the continuous-ROUND loop

The build method is openAG's core thesis made concrete:

> Start with a **breadth-complete skeleton of mostly-open promises and typed
> gaps**. Discharge each promise (`open → delivered → verified`) as
> information arrives. **The gap register is the "what do we still need to
> know" worklist.**

- **Breadth-first, then depth.** Pass 1 makes every real subsystem/component
  of the cell appear as a node (nothing structurally missing), each with 2–4
  promises plus geometry/kinematic/live **hooks** — mostly `status: open` or
  `typed-gap`.
- **Incremental grounding.** The modeler feeds information over time; each
  increment discharges promises and shrinks the gap register. This is openAG
  promise-discharge, hand-run without an engine.

No engine exists, so the "engine" is the modeler + this design + the
conformance checklist. That is itself a validation data-point (G1).

---

## 3. Two repositories

| repo | holds | why |
|---|---|---|
| **This repo (AMS)** | openAG **standard extensions** under `docs/openAG/` (+ any schema sketch). | openAG standard docs already live here; findings loop straight back. Doc-only — AMS-frozen rule intact. |
| **New: `heller-cell-model`** | the hand-authored model, `FINDINGS.md`, `CONFORMANCE.md`. | It is a real system model, not AMS code — clean separation. |

---

## 4. openAG standard extensions (this repo — Phase 1)

The standard currently defines **software-flavored node kinds** and **seven
axes** with **no geometry**. To let the model capture the whole cell, the
standard gains six additive extensions (all backward-compatible):

1. **Domain profiles** — port the AMS `controls` / `mechanical` / `electrical`
   profiles into the openAG standard. Component subkinds (`machine-tool`,
   `robot`, `plc-program`, `drive`, `sensor`, `actuator`,
   `safety-controller`, `tool-changer`, `pump`, …), discipline tags, and
   discipline attributes (`safety_integrity_level` 0–4, `material`,
   `mass_kg`, `dimensions_mm`, `voltage`, …).
2. **A8 — Spatial / Geometric axis** (seven → eight axes). Relationship
   types: `mounted-on`, `adjacent-to`, `mates-with`, `connected-at`,
   `routed-through`; plus a coordinate-frame concept.
   *Alternative to validate:* is geometry "just promises" needing no new
   axis? Spatial **relationships** argue for the axis. Finding-worthy.
3. **Geometry promise vocabulary** — attributes `geometry_ref` (CAD/mesh
   URI), `pose` (frame + transform), `bounding_box`, `coordinate_frame`.
4. **Kinematics vocabulary** — joints + DH/URDF-style descriptors,
   `motion-profile` / `kinematic-chain` behaviors, reach envelope.
5. **Live-data binding vocabulary** — dynamic promises carry a binding
   descriptor (OPC-UA node id / PLC tag / historian ref) that the **runtime
   oracle** grounds. A `verified` dynamic promise = live-confirmed state.
6. **Oracle set** — cyber-physical grounding needs code-scan (PLC/robot
   code), human-dialogue, model-self, runtime (OPC-UA/SCADA) — and possibly
   a 5th **metrology/CAD** oracle for geometry (or geometry grounds as
   "static evidence"). Finding-worthy.

Plus: update the **conformance checklist** (§10 of `standard.md`) and
regenerate the affected PDFs.

**These extensions are additive and doc-only.** No AMS code changes; the
AMS-frozen rule holds.

---

## 5. The Heller Cell model (new repo — Phases 2–3)

Breadth-complete, depth-shallow. Target layout:

```
heller-cell-model/
  README.md
  FINDINGS.md            ← the G1 deliverable
  CONFORMANCE.md         ← manual check vs standard §10
  model/
    system.v3.yaml       ← System L0 + mission F0
    components.v3.yaml    ← A1 partition, all subsystems/components
    capabilities.v3.yaml  ← 6 F-blocks + realizes
    actors.v3.yaml        ← operators, maintenance, MES + the oracles
    interfaces.v3.yaml    ← fieldbus / OPC-UA / robot comms / DB links
    constraints.v3.yaml   ← safety (SIL), cycle-time, availability
    relationships.v3.yaml ← axis-tagged edges (A1..A8)
```

### 5.1 A1 containment — the strict partition (conservation law)

System → exactly-one-parent children:

- `SUB-CNC` — contains 5× `machine-tool` (each contains its `tool-changer`).
- `SUB-MATHANDLING` — 2× `robot` + part store + tool store.
- `SUB-COOLANT` — pumps, tanks, distribution.
- `SUB-CONTROL` — the PLCs (`plc-program` / `safety-controller`).
- `SUB-SUPERVISORY` — SCADA + servers + DBs.

**Cross-cutting escape:** *comms* and *safety* do not belong to one
partition; they escape via a dedicated shared component or a
`LAY-CrossCutting` layer (standard §2). This is **finding #1**.

### 5.2 Capabilities (A2 `realizes`, many-to-many) + mission

- System mission **F0** (promise): "machine parts to spec via the Heller
  cell at target throughput."
- `CAP-Machining`, `CAP-MaterialFlow`, `CAP-ToolFlow`, `CAP-CoolantMgmt`,
  `CAP-CellControl`, `CAP-Supervision` — each `realizes`-linked to the
  components above.

### 5.3 Interfaces + the two-promise rule

Standard §5.2 demands every interface carry a **static** and a **dynamic**
promise. Pass 1 does this fully for a representative few (robot↔PLC
fieldbus, PLC↔SCADA OPC-UA, SCADA↔DB) and emits honest `gap:missing` dynamic
promises on the rest. The two-promise burden at scale is **finding-worthy**.

### 5.4 Actors + the four (five?) oracles

External actors (operator, maintenance, MES/ERP upstream) plus the openAG
oracle actors made explicit: code-scan (PLC/robot programs), human-dialogue
(modeler), model-self, runtime (SCADA historian), and the candidate
metrology/CAD oracle for geometry.

### 5.5 Promise authoring convention

Each promise carries `attribute`, `content`, `owner_entity`, `status`,
**`axis`** (A1–A8), **`valence`** (the kind-rule that demanded it),
`gap_type` when `typed-gap`. Each component also carries geometry /
kinematic / live **hooks** as `open` / `typed-gap` placeholders — proving
the model *can* hold them without populating them yet.

---

## 6. Validation / conformance (Phase 4)

No `openag` binary exists → conformance = **manual review against the
standard's conformance checklist** (extended with the new axis / profile /
twin requirements), recorded in `CONFORMANCE.md`. A later experiment: try
AMS's Stage-1 graph-export/validator — it will **not** validate cleanly
because of the net-new `axis`/`valence`/geometry fields, which is itself a
finding.

---

## 7. FINDINGS.md — the G1 deliverable

A running log of every strain the real system puts on the standard. Seeded
from this brainstorming:

1. **Cross-cutting partition** — comms + safety break the A1 strict
   partition; how cleanly does the escape hatch work?
2. **No spatial axis** — the seven axes carry no geometry; a twin forces A8.
3. **Two-promise burden** — static + dynamic on every interface is heavy at
   cell scale.
4. **No domain-profile mechanism** — openAG had only software kinds; a
   multi-disciplinary cell needs controls/mechanical/electrical.
5. **Oracle mapping for cyber-physical** — do four oracles suffice, or is a
   5th metrology/CAD oracle needed?
6. **Geometry: promise vs axis** — is geometry attributes-only, or does it
   need the A8 relationship axis? (Likely both.)
7. **Engine-less validation** — conformance by hand/checklist; what does the
   absence of the engine cost?

---

## 8. Beyond pass 1 (downstream, separate)

All projection/runtime work, out of scope here but not precluded by the
model shape:

- **Stage 1** — geometry population (real CAD refs, frames, layout poses).
- **Stage 2** — kinematic / simulation (joints, reach envelopes, cycle sim).
- **Stage 3** — live data binding (OPC-UA/SCADA → runtime oracle → live
  promise grounding).

Each is a projection or binding over the same graph; the breadth-first
skeleton must not preclude them (it does not).

---

## 9. Execution order

1. **Phase 0** — this design doc. ✅
2. **Phase 1** — extend the openAG standard (domain profiles, A8 axis, twin
   vocab, oracle set, conformance checklist); regenerate PDFs.
3. **PAUSE** for review before authoring.
4. **Phase 2** — scaffold `heller-cell-model`.
5. **Phase 3** — author the breadth-complete skeleton.
6. **Phase 4** — conformance check + seed `FINDINGS.md`.
7. **Ongoing** — modeler feeds info; promises discharge; gap register shrinks.

---

## 10. Non-goals (explicit)

- No 3D rendering, CAD acquisition, physics, kinematics runtime, or live
  data wiring in this work.
- No openAG engine implementation (still deferred; hand-authored).
- No AMS code changes (AMS frozen until parity; extensions are doc-only).
