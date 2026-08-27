---
document: Risk Assessment
system: architecture-model-standard
system_id: SYS-unknown
generated_at: 2026-08-27T14:23:21Z
generator_version: 0.3.0
model_hash: 08abc716587d
edition: 9
---

# Risk Assessment: architecture-model-standard

## Risk Register

| Risk ID | Category | Severity | Description | Mitigation |
|---------|----------|----------|-------------|------------|
| RISK-DEP-COMP-1.1 | Dependency | HIGH | Type System has 5 dependents — single point of failure | Ensure thorough testing of Type System; consider interface abstraction |
| RISK-DEP-COMP-3 | Dependency | MEDIUM | Manifest has 3 dependents | Monitor for breaking changes |
| RISK-DEP-COMP-3.1 | Dependency | MEDIUM | Scanners has 3 dependents | Monitor for breaking changes |
| RISK-DEP-COMP-9 | Dependency | MEDIUM | Configuration has 4 dependents | Monitor for breaking changes |
| RISK-CON-CON-1 | Constraint | MEDIUM | Constraint 'Python >=3.11' (technology) has no verification | Add verification tests or monitoring |
| RISK-CON-CON-2 | Constraint | MEDIUM | Constraint 'CI/CD: GitHub Actions' (technology) has no verification | Add verification tests or monitoring |

## Dependency Risks

Components with high dependency count (fragile to upstream changes):

| Component | Dependencies (fan-out) |
|-----------|----------------------|
| CLI | 6 |

## Constraint Risks

**Unallocated constraints (no component owns them):**

- Python >=3.11 (technology)
- CI/CD: GitHub Actions (technology)
