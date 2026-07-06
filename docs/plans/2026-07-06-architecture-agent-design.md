# Architecture Agent System Design

> **Strategic decision:** Split the architecture-model-standard training layer into two new repositories, creating a self-improving architecture extraction and code generation system deployed as an OpenCode extension + HuggingFace model.

**Date:** 2026-07-06
**Status:** Approved
**Repos:** `opencode-arch`, `arch-agent`

---

## Vision

The system learns from its own usage. Every extraction, every code generation, every validation produces training signal. The oracle (frontier model) scores surrogate outputs, DPO pairs accumulate, the surrogate improves, and the cycle tightens. Both the oracle pipeline (prompt strategies, scoring heuristics) and the surrogate (extraction quality, code generation) improve through the self-learning loop.

```
                         SELF-LEARNING LOOP
                    (improves with every use)

    ┌─────────────────────────────────────────────────────┐
    │                                                     │
    │   User invokes via OpenCode                         │
    │        │                                            │
    │        ▼                                            │
    │   opencode-arch (MCP)                               │
    │        │                                            │
    │        ├──► Surrogate extracts/generates            │
    │        │         │                                  │
    │        │         ▼                                  │
    │        ├──► Oracle scores result                    │
    │        │         │                                  │
    │        │         ▼                                  │
    │        ├──► DPO pair stored                         │
    │        │         │                                  │
    │        │         ▼                                  │
    │        └──► arch-agent trains on pairs              │
    │                  │                                  │
    │                  ▼                                  │
    │             Better model published to HF            │
    │                  │                                  │
    │                  ▼                                  │
    │             opencode-arch pulls improved model      │
    │                  │                                  │
    └──────────────────┘ (loop tightens)                  │
                                                          │
    Oracle pipeline also improves:                        │
    - Better scoring heuristics                           │
    - Better prompt strategies                            │
    - Better context slicing                              │
    └─────────────────────────────────────────────────────┘
```

---

## Three-Repo Architecture

### architecture-model-standard (EXISTING - becomes schema-only)

Remains the **specification layer** — the open standard that defines the 7 entities, 8 relationships, validation rules, and CLI tooling.

**Keeps:**
- Schema (7 entity types, 8 relationship types)
- Core types, parser, validator, slicer, differ
- Manifest generator (AST scanning)
- CLI (init, validate, slice, diff, query, context, stats, impact)
- JSON Schema (spec/)
- Integration bridge (enrich_manifest_slice)
- Documentation (specification, LLM protocol, project descriptor)

**Removes:**
- `src/architecture_model/training/` (39 files, 10.6K lines) → moves to arch-agent

**Role:** The lingua franca. Both opencode-arch and arch-agent depend on this for types/schema.

---

### opencode-arch (NEW - OpenCode extension)

The **interface layer** — how users interact with the system. MCP server + skills.

**Responsibilities:**
- MCP server exposing 6 tools to OpenCode sessions
- Oracle pipeline (calls copilot-relay or litellm for scoring)
- Prompt engineering / scoring heuristic evolution (self-improving)
- Context slicing / token broker (the compression engine)
- Telemetry collection and anonymization
- Workflow skills for common patterns

**Structure:**
```
opencode-arch/
├── src/opencode_arch/
│   ├── mcp/
│   │   ├── server.py              — FastMCP entry point
│   │   └── tools/
│   │       ├── extract.py         — architect_extract (code → UAM)
│   │       ├── generate.py        — architect_generate (UAM → code)
│   │       ├── validate.py        — architect_validate (score)
│   │       ├── slice.py           — architect_slice (token broker)
│   │       ├── document.py        — architect_document (artifacts)
│   │       └── train.py           — architect_train (learning step)
│   │
│   ├── oracle/                    — Oracle integration
│   │   ├── copilot_relay.py       — SSE adapter (from this session's work)
│   │   ├── scorer.py              — Extraction quality scoring
│   │   └── prompt_evolution.py    — Self-improving prompt strategies
│   │
│   ├── context/                   — Context compression engine
│   │   ├── slicer.py              — Graph-aware sub-model extraction
│   │   ├── formatter.py           — LLM-optimized context formatting
│   │   └── budget.py              — Token budget management
│   │
│   ├── telemetry/                 — Anonymized data export
│   │   ├── anonymizer.py          — Strip code, keep structural tokens
│   │   └── contributor.py         — Opt-in upload to HF dataset
│   │
│   └── config.py                  — Model endpoint, oracle config, telemetry opt-in
│
├── skills/                        — OpenCode skill definitions
│   ├── extraction/SKILL.md        — "Extract architecture from this repo"
│   ├── generation/SKILL.md        — "Generate code from architecture model"
│   └── review/SKILL.md            — "Review changes for architectural impact"
│
├── tests/
├── pyproject.toml
└── README.md
```

**Dependencies:**
- `architecture-model-standard` — schema, types, validation
- `mcp` — FastMCP server framework
- `aiohttp` — HTTP client for oracle/model calls
- `arch-agent` — (optional) for local training

**Self-learning in opencode-arch:**
- Oracle scoring heuristics adapt based on downstream model improvement
- Prompt strategies evolve (PromptEvolver pattern from current training/)
- Context slicing depth adjusts based on generation success rates

---

### arch-agent (NEW - HuggingFace model + training)

The **brain layer** — the trained model and the machinery that improves it.

**Responsibilities:**
- Surrogate model inference (local Ollama or HF Inference API)
- Training pipeline (DPO pairs → LoRA training → publish)
- Model registry and adapter management
- HF Spaces demo (interactive architecture extraction)
- Community dataset management
- Test-guided generation (the forward pass)

**Structure:**
```
arch-agent/
├── src/arch_agent/
│   ├── training/                  — MOVED from architecture-model-standard
│   │   ├── surrogate.py           — Ollama client
│   │   ├── pipeline.py            — Training orchestrator
│   │   ├── evaluator.py           — Multi-objective loss
│   │   ├── trainer.py             — LoRA trainer (HF PEFT)
│   │   ├── trainer_dpo.py         — DPO preference trainer
│   │   ├── test_guided_generator.py
│   │   ├── test_contract_miner.py
│   │   ├── failure_parser.py
│   │   ├── code_writer.py
│   │   ├── prompt_builder.py
│   │   └── ... (29 more modules)
│   │
│   ├── models/                    — Model registry + HF integration
│   │   ├── registry.py            — Model configs, adapter catalog
│   │   ├── hf_publisher.py        — Push adapters to HF Hub
│   │   ├── hf_inference.py        — Call HF Inference API
│   │   └── local_inference.py     — Local Ollama inference
│   │
│   ├── dataset/                   — Training data management
│   │   ├── collector.py           — Ingest DPO pairs from opencode-arch
│   │   ├── store.py               — SQLite training store
│   │   ├── anonymizer.py          — Structural token extraction
│   │   └── hf_sync.py             — Sync with HF Datasets
│   │
│   └── spaces/                    — HF Spaces demo
│       └── app.py                 — Gradio interface
│
├── tests/                         — 619+ tests (moved from architecture-model-standard)
├── pyproject.toml
└── README.md
```

**HuggingFace Presence:**
- **Model:** `anomalyco/arch-agent` — LoRA adapters (qwen2.5/llama base)
- **Dataset:** `anomalyco/arch-agent-data` — Anonymized structural tokens
- **Space:** `anomalyco/arch-agent-demo` — Interactive extraction demo

**Self-learning in arch-agent:**
- Surrogate model improves via DPO training on oracle-scored pairs
- Both extraction (code → UAM) and generation (UAM → code) improve
- Test pass rate serves as objective ground truth signal
- Model quality tracked over time with Pareto convergence

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER SESSION                              │
│                                                                  │
│  OpenCode ──► opencode-arch MCP Server                          │
│                    │                                             │
│                    ├─── architect_extract ─────┐                 │
│                    │        │                  │                 │
│                    │        ▼                  │                 │
│                    │   arch-agent inference    │                 │
│                    │   (local or HF API)       │                 │
│                    │        │                  │                 │
│                    │        ▼                  │                 │
│                    │   Oracle scores result    │                 │
│                    │   (copilot-relay)         │                 │
│                    │        │                  │                 │
│                    │        ▼                  │                 │
│                    │   DPO pair stored         │                 │
│                    │                           │                 │
│                    ├─── architect_generate ────┤                 │
│                    │        │                  │                 │
│                    │        ▼                  │                 │
│                    │   arch-agent generates    │                 │
│                    │   Tests run as oracle     │                 │
│                    │   Pass rate = reward      │                 │
│                    │        │                  │                 │
│                    │        ▼                  │                 │
│                    │   Training signal stored  │                 │
│                    │                           │                 │
│                    ├─── architect_train ───────┘                 │
│                    │        │                                    │
│                    │        ▼                                    │
│                    │   arch-agent trains on accumulated pairs    │
│                    │   Publishes improved adapter to HF          │
│                    │                                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase 1 MVP (Minimum Viable)

| Repo | Deliverable |
|------|-------------|
| `opencode-arch` | MCP server with `architect_extract` + `architect_validate`. Calls Ollama locally. Oracle scoring via copilot-relay. 1 skill (extraction workflow). |
| `arch-agent` | Training pipeline (moved). First LoRA adapter published to HF. Basic HF model card. |
| `architecture-model-standard` | Remove training/, update deps, bump to v0.4.0 |

**Phase 1 proves:** User extracts architecture via OpenCode → quality improves over time → model gets better.

---

## Key Technical Decisions

1. **Oracle stays in opencode-arch** — It's the scoring layer, not the model layer. Frontier model access lives where the user runs (their OpenCode session).

2. **Training can happen locally or remotely** — arch-agent supports both Ollama-based local training and HF Spaces cloud training.

3. **Both sides improve** — The oracle pipeline's prompt strategies evolve based on what makes the surrogate produce better results. The surrogate improves via DPO. Bidirectional self-improvement.

4. **Anonymization is key** — Community dataset only contains graph topology (entity counts, relationship types, structural patterns). No code, no names, no IP.

5. **architecture-model-standard stays lean** — Schema + validation + CLI. The "open standard" that anyone can implement against without needing the ML stack.
