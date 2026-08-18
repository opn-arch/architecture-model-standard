---
document: Maintenance Manual
system: Projects (views)
system_id: SYS-unknown
generated_at: 2026-08-18T12:32:32Z
generator_version: 0.3.0
model_hash: a4f321da275c
edition: 3
---

# Maintenance Manual: Projects (views)

## Component Inventory

| Component | Kind | Layer | Files | Signatures | Test Contracts |
|-----------|------|-------|-------|-----------|----------------|
| Csrf (COMP-15) | service | — | 4 | 0 | 0 |
| Debug (COMP-16) | service | — | 2 | 0 | 0 |
| Cache (COMP-17) | service | — | 1 | 0 | 0 |
| Clickjacking (COMP-18) | service | — | 1 | 0 | 0 |
| Csp (COMP-19) | service | — | 1 | 0 | 0 |
| Http (COMP-20) | service | — | 1 | 0 | 0 |
| Vary (COMP-21) | service | — | 1 | 0 | 0 |
| Defaults (COMP-22) | service | — | 1 | 0 | 0 |
| Dates (COMP-23) | service | — | 1 | 0 | 0 |
| Detail (COMP-24) | service | — | 1 | 0 | 0 |
| Edit (COMP-25) | service | — | 1 | 0 | 0 |
| List (COMP-26) | service | — | 1 | 0 | 0 |
| I18N (COMP-27) | service | — | 1 | 0 | 0 |
| Static (COMP-28) | service | — | 1 | 0 | 0 |
| Infrastructure (COMP-29) | service | — | 1 | 0 | 0 |

## Dependency Impact Analysis

| Component | Depends On (fan-out) | Depended By (fan-in) | Impact Risk |
|-----------|---------------------|---------------------|-------------|
| Csrf | Clickjacking, Vary, Cache, Http, Debug, Csp, Infrastructure | Defaults, Http, Edit, Debug, Cache, Dates, Detail, I18N, List | HIGH |
| Debug | Clickjacking, Static, Vary, Cache, Http, Csrf, Csp, Infrastructure, Defaults, I18N | Http, Edit, Defaults, Cache, Csrf, List, Dates, Detail, I18N | HIGH |
| Cache | Http, Debug, Csrf, Csp, Infrastructure, Clickjacking, Vary | Http, Debug, Csrf, Vary, Defaults | HIGH |
| Clickjacking | — | Csrf, Debug, Defaults, Http, Cache | HIGH |
| Csp | — | Defaults, Http, Debug, Cache, Csrf | HIGH |
| Http | Cache, Debug, Csrf, Csp, Infrastructure, Clickjacking, Vary | Edit, Debug, Cache, Csrf, List, Static, Dates, Detail, I18N, Defaults | HIGH |
| Vary | Cache | Csrf, Debug, Defaults, Http, Cache | HIGH |
| Defaults | Csrf, Csp, Debug, Infrastructure, I18N, Clickjacking, Static, Vary, Cache, Http | List, Dates, Detail, I18N, Edit, Debug | HIGH |
| Dates | Edit, I18N, Detail, Defaults, Static, Csrf, Http, Debug, List | Edit, List, I18N, Detail | MEDIUM |
| Detail | List, Edit, I18N, Defaults, Static, Csrf, Http, Debug, Dates | Dates, I18N, Edit, List | MEDIUM |
| Edit | Http, Debug, Csrf, Dates, Detail, Defaults, List, I18N, Static | Dates, Detail, I18N, List | MEDIUM |
| List | Defaults, Edit, I18N, Static, Http, Debug, Csrf, Dates, Detail | Detail, I18N, Edit, Dates | MEDIUM |
| I18N | List, Edit, Detail, Defaults, Static, Csrf, Dates, Http, Debug | Dates, Detail, List, Defaults, Edit, Debug | HIGH |
| Static | Http | Debug, I18N, List, Dates, Detail, Defaults, Edit | HIGH |
| Infrastructure | — | Defaults, Http, Debug, Cache, Csrf | HIGH |

## Modification Procedures

For each component, the following files and dependencies must be considered:

### Csrf (COMP-15)

**Files:**
- `projects/django/django/views/csrf.py`
- `projects/django/django/views/decorators/csrf.py`
- `projects/django/django/views/decorators/gzip.py`
- `projects/django/django/views/generic/base.py`
**Downstream dependents (must re-test):** Defaults, Http, Edit, Debug, Cache, Dates, Detail, I18N, List

### Debug (COMP-16)

**Files:**
- `projects/django/django/views/debug.py`
- `projects/django/django/views/decorators/debug.py`
**Downstream dependents (must re-test):** Http, Edit, Defaults, Cache, Csrf, List, Dates, Detail, I18N

### Cache (COMP-17)

**Files:**
- `projects/django/django/views/decorators/cache.py`
**Downstream dependents (must re-test):** Http, Debug, Csrf, Vary, Defaults

### Clickjacking (COMP-18)

**Files:**
- `projects/django/django/views/decorators/clickjacking.py`
**Downstream dependents (must re-test):** Csrf, Debug, Defaults, Http, Cache

### Csp (COMP-19)

**Files:**
- `projects/django/django/views/decorators/csp.py`
**Downstream dependents (must re-test):** Defaults, Http, Debug, Cache, Csrf

### Http (COMP-20)

**Files:**
- `projects/django/django/views/decorators/http.py`
**Downstream dependents (must re-test):** Edit, Debug, Cache, Csrf, List, Static, Dates, Detail, I18N, Defaults

### Vary (COMP-21)

**Files:**
- `projects/django/django/views/decorators/vary.py`
**Downstream dependents (must re-test):** Csrf, Debug, Defaults, Http, Cache

### Defaults (COMP-22)

**Files:**
- `projects/django/django/views/defaults.py`
**Downstream dependents (must re-test):** List, Dates, Detail, I18N, Edit, Debug

### Dates (COMP-23)

**Files:**
- `projects/django/django/views/generic/dates.py`
**Downstream dependents (must re-test):** Edit, List, I18N, Detail

### Detail (COMP-24)

**Files:**
- `projects/django/django/views/generic/detail.py`
**Downstream dependents (must re-test):** Dates, I18N, Edit, List

### Edit (COMP-25)

**Files:**
- `projects/django/django/views/generic/edit.py`
**Downstream dependents (must re-test):** Dates, Detail, I18N, List

### List (COMP-26)

**Files:**
- `projects/django/django/views/generic/list.py`
**Downstream dependents (must re-test):** Detail, I18N, Edit, Dates

### I18N (COMP-27)

**Files:**
- `projects/django/django/views/i18n.py`
**Downstream dependents (must re-test):** Dates, Detail, List, Defaults, Edit, Debug

### Static (COMP-28)

**Files:**
- `projects/django/django/views/static.py`
**Downstream dependents (must re-test):** Debug, I18N, List, Dates, Detail, Defaults, Edit

### Infrastructure (COMP-29)

**Files:**
- `projects/django/django/views/decorators/common.py`
**Downstream dependents (must re-test):** Defaults, Http, Debug, Cache, Csrf

## Known Constraints

*No constraint allocations defined.*
