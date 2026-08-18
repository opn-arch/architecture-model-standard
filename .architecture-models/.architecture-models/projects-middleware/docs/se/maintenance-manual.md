---
document: Maintenance Manual
system: Projects (middleware)
system_id: SYS-unknown
generated_at: 2026-08-18T12:32:29Z
generator_version: 0.3.0
model_hash: ad0657be9014
edition: 3
---

# Maintenance Manual: Projects (middleware)

## Component Inventory

| Component | Kind | Layer | Files | Signatures | Test Contracts |
|-----------|------|-------|-------|-----------|----------------|
| Cache (COMP-1) | service | — | 1 | 0 | 0 |
| Clickjacking (COMP-2) | service | — | 1 | 0 | 0 |
| Common (COMP-3) | service | — | 1 | 0 | 0 |
| Csp (COMP-4) | service | — | 1 | 0 | 0 |
| Csrf (COMP-5) | service | — | 1 | 0 | 0 |
| Gzip (COMP-6) | service | — | 1 | 0 | 0 |
| Http (COMP-7) | service | — | 1 | 0 | 0 |
| Locale (COMP-8) | service | — | 1 | 0 | 0 |
| Security (COMP-9) | service | — | 1 | 0 | 0 |

## Dependency Impact Analysis

| Component | Depends On (fan-out) | Depended By (fan-in) | Impact Risk |
|-----------|---------------------|---------------------|-------------|
| Cache | Security, Csp, Common, Gzip, Clickjacking, Locale, Csrf, Http | Security, Http, Common, Locale, Csrf, Csp, Gzip, Clickjacking | HIGH |
| Clickjacking | Csrf, Http, Csp, Security, Common, Gzip, Locale, Cache | Common, Csrf, Csp, Locale, Cache, Gzip, Security, Http | HIGH |
| Common | Gzip, Clickjacking, Locale, Cache, Csrf, Security, Http, Csp | Csrf, Locale, Csp, Cache, Gzip, Clickjacking, Security, Http | HIGH |
| Csp | Common, Gzip, Clickjacking, Locale, Cache, Csrf, Http, Security | Cache, Gzip, Clickjacking, Security, Http, Common, Locale, Csrf | HIGH |
| Csrf | Common, Gzip, Clickjacking, Locale, Cache, Http, Security, Csp | Clickjacking, Security, Http, Common, Locale, Csp, Cache, Gzip | HIGH |
| Gzip | Http, Csp, Security, Common, Clickjacking, Locale, Cache, Csrf | Common, Locale, Csrf, Csp, Cache, Clickjacking, Security, Http | HIGH |
| Http | Locale, Cache, Csrf, Security, Csp, Common, Gzip, Clickjacking | Gzip, Clickjacking, Security, Common, Csrf, Locale, Csp, Cache | HIGH |
| Locale | Common, Gzip, Clickjacking, Cache, Csrf, Http, Csp, Security | Http, Common, Csrf, Csp, Cache, Gzip, Clickjacking, Security | HIGH |
| Security | Cache, Csrf, Http, Csp, Common, Gzip, Clickjacking, Locale | Cache, Gzip, Clickjacking, Http, Common, Csrf, Locale, Csp | HIGH |

## Modification Procedures

For each component, the following files and dependencies must be considered:

### Cache (COMP-1)

**Files:**
- `projects/django/django/middleware/cache.py`
**Downstream dependents (must re-test):** Security, Http, Common, Locale, Csrf, Csp, Gzip, Clickjacking

### Clickjacking (COMP-2)

**Files:**
- `projects/django/django/middleware/clickjacking.py`
**Downstream dependents (must re-test):** Common, Csrf, Csp, Locale, Cache, Gzip, Security, Http

### Common (COMP-3)

**Files:**
- `projects/django/django/middleware/common.py`
**Downstream dependents (must re-test):** Csrf, Locale, Csp, Cache, Gzip, Clickjacking, Security, Http

### Csp (COMP-4)

**Files:**
- `projects/django/django/middleware/csp.py`
**Downstream dependents (must re-test):** Cache, Gzip, Clickjacking, Security, Http, Common, Locale, Csrf

### Csrf (COMP-5)

**Files:**
- `projects/django/django/middleware/csrf.py`
**Downstream dependents (must re-test):** Clickjacking, Security, Http, Common, Locale, Csp, Cache, Gzip

### Gzip (COMP-6)

**Files:**
- `projects/django/django/middleware/gzip.py`
**Downstream dependents (must re-test):** Common, Locale, Csrf, Csp, Cache, Clickjacking, Security, Http

### Http (COMP-7)

**Files:**
- `projects/django/django/middleware/http.py`
**Downstream dependents (must re-test):** Gzip, Clickjacking, Security, Common, Csrf, Locale, Csp, Cache

### Locale (COMP-8)

**Files:**
- `projects/django/django/middleware/locale.py`
**Downstream dependents (must re-test):** Http, Common, Csrf, Csp, Cache, Gzip, Clickjacking, Security

### Security (COMP-9)

**Files:**
- `projects/django/django/middleware/security.py`
**Downstream dependents (must re-test):** Cache, Gzip, Clickjacking, Http, Common, Csrf, Locale, Csp

## Known Constraints

*No constraint allocations defined.*
