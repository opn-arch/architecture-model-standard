---
document: Risk Assessment
system: architecture-model-standard/Pipeline
system_id: SYS-unknown
generated_at: 2026-08-27T14:23:22Z
generator_version: 0.3.0
model_hash: 18454899275b
edition: 1
---

# Risk Assessment: architecture-model-standard/Pipeline

## Risk Register

| Risk ID | Category | Severity | Description | Mitigation |
|---------|----------|----------|-------------|------------|
| RISK-CON-CON-NO-LLM | Constraint | MEDIUM | Constraint 'No LLM in Core' (technology) has no verification | Add verification tests or monitoring |
| RISK-CON-CON-PERF | Constraint | MEDIUM | Constraint 'Pipeline Performance' (technology) has no verification | Add verification tests or monitoring |

## Dependency Risks

Components with high dependency count (fragile to upstream changes):

| Component | Dependencies (fan-out) |
|-----------|----------------------|
| Pipeline | 3 |

## Constraint Risks

*All constraints allocated.*
