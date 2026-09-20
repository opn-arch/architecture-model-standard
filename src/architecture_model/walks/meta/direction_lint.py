"""architecture_model.walks.meta.direction_lint — edge-level note-direction linter.

Scans every relationship for note-text patterns that describe the opposite
direction of the stored edge (L2/L9 lesson from realizes-direction-fix).
Returns a deterministic list of warning dicts.

This is a Python meta-walk (not a declarative WalkSpec) because its subject
is the model's relationship data — the WalkSpec DSL walks over entities and
their attributes, not over edges and their note text. Realizes
``CAP-WK.direction-lint``.

Patterns caught (case-insensitive on lowercased note):

* ``"<X> is realized by <Y>"`` on edge ``X -> realizes -> Y`` (expects ``Y -> X``)
* ``"<X> depends on <Y>"``     on edge ``Y -> depends-on -> X`` (expects ``X -> Y``)
* ``"<X> is contained in <Y>"`` on edge ``X -> contains -> Y`` (expects ``Y -> X``)
* ``"<X> exposes <Y>"``        on edge ``Y -> exposes -> X`` (expects ``X -> Y``)

IDs in the note are matched by substring on the stored ``from``/``to`` ids,
so both bare ids (``CAP-PB``) and qualified references (``CAP-PB Extract``)
trigger the same rule.
"""

from __future__ import annotations

from typing import Any

__all__ = ["lint_edge_note_directions"]


def lint_edge_note_directions(relationships: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return a deterministic list of ``{from, to, type, note, warning}`` dicts.

    Empty list means the model is clean (no note-vs-direction contradictions).
    Sort key: ``(type, from, to)``.
    """
    warnings: list[dict[str, Any]] = []
    for r in relationships:
        f, t, rt = r.get("from"), r.get("to"), r.get("type")
        note = (r.get("note") or "").lower()
        if not (f and t and rt and note):
            continue
        f_l, t_l = str(f).lower(), str(t).lower()

        rules = [
            ("realizes",   f"{f_l} is realized by", f"{t_l} realizes"),
            ("depends-on", f"{t_l} depends on",     f"{f_l} depends on"),
            ("contains",   f"{f_l} is contained",   f"{t_l} contains"),
            ("exposes",    f"{t_l} exposes",        f"{f_l} exposes"),
        ]
        for rule_type, wrong_pattern, right_pattern in rules:
            if rt != rule_type:
                continue
            if wrong_pattern in note and right_pattern not in note:
                warnings.append(
                    {
                        "from": f,
                        "to": t,
                        "type": rt,
                        "note": r.get("note", ""),
                        "warning": (
                            f"note text suggests {rule_type} direction is "
                            f"reversed (expected {t}->{f})"
                        ),
                    }
                )
                break
    return sorted(warnings, key=lambda w: (w["type"], w["from"], w["to"]))
