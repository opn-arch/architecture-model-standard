---
document: Maintenance Manual
system: Projects (template)
system_id: SYS-unknown
generated_at: 2026-08-18T12:32:30Z
generator_version: 0.3.0
model_hash: 7f71c642a524
edition: 3
---

# Maintenance Manual: Projects (template)

## Component Inventory

| Component | Kind | Layer | Files | Signatures | Test Contracts |
|-----------|------|-------|-------|-----------|----------------|
| Autoreload (COMP-15) | service | — | 1 | 0 | 0 |
| Django (COMP-16) | service | — | 6 | 0 | 0 |
| Dummy (COMP-17) | service | — | 1 | 0 | 0 |
| Jinja2 (COMP-18) | service | — | 1 | 0 | 0 |
| Context (COMP-19) | service | — | 2 | 0 | 0 |
| Defaultfilters (COMP-21) | service | — | 1 | 0 | 0 |
| Defaulttags (COMP-22) | service | — | 1 | 0 | 0 |
| Engine (COMP-23) | service | — | 1 | 0 | 0 |
| Exceptions (COMP-24) | service | — | 1 | 0 | 0 |
| Library (COMP-25) | service | — | 1 | 0 | 0 |
| Loader (COMP-26) | service | — | 2 | 0 | 0 |
| App Directories (COMP-28) | service | — | 1 | 0 | 0 |
| Cached (COMP-29) | service | — | 1 | 0 | 0 |
| Filesystem (COMP-30) | service | — | 1 | 0 | 0 |
| Locmem (COMP-31) | service | — | 1 | 0 | 0 |
| Response (COMP-32) | service | — | 1 | 0 | 0 |
| Smartif (COMP-33) | service | — | 1 | 0 | 0 |

## Dependency Impact Analysis

| Component | Depends On (fan-out) | Depended By (fan-in) | Impact Risk |
|-----------|---------------------|---------------------|-------------|
| Autoreload | Jinja2, Library, Defaultfilters, Response, Dummy, Django, Engine, Context, Smartif, Exceptions, Defaulttags, Loader | Locmem, Cached, Filesystem, Django, Jinja2, Dummy, App Directories | HIGH |
| Django | Defaultfilters, Autoreload, Engine, Response, Context, Smartif, Exceptions, Defaulttags, Loader, Library | Cached, Defaultfilters, Library, Defaulttags, Locmem, Context, Jinja2, Response, Dummy, Autoreload, Filesystem, Loader, App Directories, Engine | HIGH |
| Dummy | Response, Django, Autoreload, Engine, Loader, Context, Library, Smartif, Exceptions, Defaulttags, Defaultfilters | Cached, Autoreload | MEDIUM |
| Jinja2 | Response, Django, Autoreload, Engine, Loader, Context, Smartif, Exceptions, Defaulttags, Library, Defaultfilters | Autoreload, Cached | MEDIUM |
| Context | Django | Engine, Defaulttags, Cached, Django, Locmem, Jinja2, Dummy, Autoreload, Filesystem, App Directories | HIGH |
| Defaultfilters | Django, Library | Autoreload, Filesystem, Django, App Directories, Cached, Defaulttags, Locmem, Jinja2, Dummy | HIGH |
| Defaulttags | Context, Django, Smartif, Library, Defaultfilters | App Directories, Cached, Django, Locmem, Jinja2, Dummy, Autoreload, Filesystem | HIGH |
| Engine | Context, Library, Exceptions, Django | Cached, Filesystem, Django, Locmem, Jinja2, Dummy, Autoreload, App Directories | HIGH |
| Exceptions | — | App Directories, Engine, Cached, Library, Django, Locmem, Jinja2, Dummy, Autoreload, Filesystem, Loader | HIGH |
| Library | Django, Exceptions | App Directories, Autoreload, Engine, Loader, Defaultfilters, Defaulttags, Locmem, Cached, Dummy, Filesystem, Django, Jinja2 | HIGH |
| Loader | Library, Django, Exceptions | Locmem, Cached, Jinja2, Dummy, Filesystem, Django, Response, App Directories, Autoreload | HIGH |
| App Directories | Library, Smartif, Exceptions, Defaulttags, Defaultfilters, Autoreload, Response, Django, Engine, Loader, Filesystem, Context | — | LOW |
| Cached | Dummy, Django, Autoreload, Engine, Context, Smartif, Exceptions, Defaulttags, Loader, Jinja2, Library, Defaultfilters, Response | — | LOW |
| Filesystem | Defaultfilters, Autoreload, Engine, Response, Django, Loader, Context, Library, Smartif, Exceptions, Defaulttags | App Directories | LOW |
| Locmem | Autoreload, Response, Django, Engine, Loader, Context, Library, Smartif, Exceptions, Defaulttags, Defaultfilters | — | LOW |
| Response | Django, Loader | Locmem, Jinja2, Dummy, Autoreload, Filesystem, Django, App Directories, Cached | HIGH |
| Smartif | — | App Directories, Defaulttags, Cached, Django, Locmem, Jinja2, Dummy, Autoreload, Filesystem | HIGH |

## Modification Procedures

For each component, the following files and dependencies must be considered:

### Autoreload (COMP-15)

**Files:**
- `projects/django/django/template/autoreload.py`
**Downstream dependents (must re-test):** Locmem, Cached, Filesystem, Django, Jinja2, Dummy, App Directories

### Django (COMP-16)

**Files:**
- `projects/django/django/template/backends/base.py`
- `projects/django/django/template/backends/django.py`
- `projects/django/django/template/backends/utils.py`
- `projects/django/django/template/base.py`
- `projects/django/django/template/loaders/base.py`
- `projects/django/django/template/utils.py`
**Downstream dependents (must re-test):** Cached, Defaultfilters, Library, Defaulttags, Locmem, Context, Jinja2, Response, Dummy, Autoreload, Filesystem, Loader, App Directories, Engine

### Dummy (COMP-17)

**Files:**
- `projects/django/django/template/backends/dummy.py`
**Downstream dependents (must re-test):** Cached, Autoreload

### Jinja2 (COMP-18)

**Files:**
- `projects/django/django/template/backends/jinja2.py`
**Downstream dependents (must re-test):** Autoreload, Cached

### Context (COMP-19)

**Files:**
- `projects/django/django/template/context.py`
- `projects/django/django/template/context_processors.py`
**Downstream dependents (must re-test):** Engine, Defaulttags, Cached, Django, Locmem, Jinja2, Dummy, Autoreload, Filesystem, App Directories

### Defaultfilters (COMP-21)

**Files:**
- `projects/django/django/template/defaultfilters.py`
**Downstream dependents (must re-test):** Autoreload, Filesystem, Django, App Directories, Cached, Defaulttags, Locmem, Jinja2, Dummy

### Defaulttags (COMP-22)

**Files:**
- `projects/django/django/template/defaulttags.py`
**Downstream dependents (must re-test):** App Directories, Cached, Django, Locmem, Jinja2, Dummy, Autoreload, Filesystem

### Engine (COMP-23)

**Files:**
- `projects/django/django/template/engine.py`
**Downstream dependents (must re-test):** Cached, Filesystem, Django, Locmem, Jinja2, Dummy, Autoreload, App Directories

### Exceptions (COMP-24)

**Files:**
- `projects/django/django/template/exceptions.py`
**Downstream dependents (must re-test):** App Directories, Engine, Cached, Library, Django, Locmem, Jinja2, Dummy, Autoreload, Filesystem, Loader

### Library (COMP-25)

**Files:**
- `projects/django/django/template/library.py`
**Downstream dependents (must re-test):** App Directories, Autoreload, Engine, Loader, Defaultfilters, Defaulttags, Locmem, Cached, Dummy, Filesystem, Django, Jinja2

### Loader (COMP-26)

**Files:**
- `projects/django/django/template/loader.py`
- `projects/django/django/template/loader_tags.py`
**Downstream dependents (must re-test):** Locmem, Cached, Jinja2, Dummy, Filesystem, Django, Response, App Directories, Autoreload

### App Directories (COMP-28)

**Files:**
- `projects/django/django/template/loaders/app_directories.py`

### Cached (COMP-29)

**Files:**
- `projects/django/django/template/loaders/cached.py`

### Filesystem (COMP-30)

**Files:**
- `projects/django/django/template/loaders/filesystem.py`
**Downstream dependents (must re-test):** App Directories

### Locmem (COMP-31)

**Files:**
- `projects/django/django/template/loaders/locmem.py`

### Response (COMP-32)

**Files:**
- `projects/django/django/template/response.py`
**Downstream dependents (must re-test):** Locmem, Jinja2, Dummy, Autoreload, Filesystem, Django, App Directories, Cached

### Smartif (COMP-33)

**Files:**
- `projects/django/django/template/smartif.py`
**Downstream dependents (must re-test):** App Directories, Defaulttags, Cached, Django, Locmem, Jinja2, Dummy, Autoreload, Filesystem

## Known Constraints

*No constraint allocations defined.*
