# API Reference

Based on the architecture model context provided, this system is a **CLI-based Python tool** (not an HTTP/REST API). The interfaces are all **library APIs** and **command-line interfaces** — there are no HTTP endpoints, route handlers, or REST controllers in the codebase.

## What This System Actually Exposes

### CLI Interfaces

The system provides two CLI entry points:

- **IF-1: main CLI** — Primary user-facing commands via `src/architecture_model/cli/main.py`
- **IF-2: runner CLI** — Pipeline runner commands

### Library APIs

All other interfaces (IF-3 through IF-16, plus all `IF-auto-*` interfaces) are **internal Python library APIs** — importable modules with classes and functions, not HTTP endpoints.

---

## Recommendation

Since this is a CLI tool with internal library APIs rather than a REST/HTTP service, the appropriate documentation formats would be:

1. **CLI Command Reference** — documenting commands, subcommands, flags, and arguments
2. **Python API Reference** — documenting public classes, methods, and function signatures

---

If you'd like, I can produce either:

- A **CLI Command Reference** based on the CLI component structure, or
- A **Library API Reference** documenting the public Python interfaces

Let me know which format would be most useful for your needs.