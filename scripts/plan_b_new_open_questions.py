"""T0.11: Additively append open_questions discovered during T0.9/T0.10 wiring.

Additive-only per user directive. Leaves T0.6-inherited open_questions
intact; each entity below receives one new appended question surfaced
by the structural wiring work.

Every question ends in `?` and is <=200 chars. Fill-if-empty is NOT
used here; these are new questions appended to existing lists.
"""

from __future__ import annotations

from pathlib import Path
from ruamel.yaml import YAML

PLAN_B = Path(".architecture-model.plan-b.yaml")

NEW_QUESTIONS = {
    "CAP-PB-LLM": "How does the pipeline recover when the LLM budget cap is breached mid-run \u2014 checkpoint-and-resume from last successful stage, or fail-hard and require re-run with higher budget?",
    "CAP-PB-ADAPTER": "Are the legacy adapters permanent bridges (indefinite) or phase-out (target removal in a specific schema generation)?",
    "COMP-PB-BUDGET-ENFORCER": "On budget breach, does the enforcer abort the stage in progress or let it finish and then abort the next stage? Which minimizes wasted spend vs partial-recovery complexity?",
    "COMP-PB-LLM-PROVIDER": "If the primary provider becomes unavailable mid-run (network / rate limit / policy fallback), does the router transparently switch providers with matching capabilities, or fail the run?",
    "COMP-PB-PROMISE-PARSER": "During the 2.1 -> 3.0 migration window, does the parser accept both schemas simultaneously (schema_version-gated dispatch) or only the current model's declared version?",
    "COMP-PB-MIGRATOR": "For lossy prose fields re-derived by LLM, is temperature=0 + fixed prompt + fixed model sufficient for byte-stable output, or is deterministic decoding required?",
    "COMP-PB-STAGE-CLUSTER": "Which embedding model backs the cluster stage \u2014 local sentence-transformers (deterministic, CPU) or remote OpenAI ada (API-dependent, higher quality)?",
    "COMP-PB-STAGE-LINK": "Are the deterministic (>=0.85) and LLM-adjudication (0.5-0.85) score thresholds correct for all promise-attribute types, or should thresholds vary per family?",
    "COMP-PB-STAGE-CONTAINERIZE": "When the LLM fallback returns different kinds on retry for the same ambiguous family, does the stage re-prompt with lower temperature, use majority vote across N samples, or fail the family with a typed gap?",
    "COMP-PB-STANDALONE-HARNESS": "Does the <30s runtime target hold on 500+ entity models, or does per-entity slice materialization need a cache keyed by (model_revision, entity_id) shared across the parametrized test session?",
    "COMP-PB-CI-GATE": "What is the escape hatch when closure legitimately regresses (deliberate scope reduction) \u2014 a PR label, a structured override annotation in the PR body, or a required approver override?",
    "COMP-PB-SIL-EVIDENCE-BINDER": "Is the 7d stale-reopen threshold uniform across promise attribute types, or should it scale (e.g. verification / tests reopen after 1d; SLOs reopen after 30d)?",
    "COMP-PB-PROMPT-LIBRARY": "When a prompt fragment is intentionally revised, are old content-hashed versions retained for replayability of prior generations, or archived out-of-band?",
}


def main() -> int:
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096
    with PLAN_B.open() as f:
        doc = yaml.load(f)

    ents = doc["entities"]
    by_id: dict[str, dict] = {}
    for coll_key in ("actors", "capabilities", "behaviors", "components", "interfaces"):
        for e in ents.get(coll_key) or []:
            by_id[e["id"]] = e

    added = 0
    for eid, question in NEW_QUESTIONS.items():
        if eid not in by_id:
            print(f"WARNING: unknown entity id: {eid}")
            continue
        oq = by_id[eid].get("open_questions") or []
        if question in oq:
            print(f"skip (dup): {eid}")
            continue
        oq.append(question)
        by_id[eid]["open_questions"] = oq
        added += 1

    with PLAN_B.open("w") as f:
        yaml.dump(doc, f)
    print(f"Appended {added} open_questions across {added} entities")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
