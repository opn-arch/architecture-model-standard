#!/usr/bin/env python3
"""Generate comprehensive markdown reference of all architecture models."""
from architecture_model.core.parser import load_model
from architecture_model.core.validator import validate_model
from pathlib import Path


def main():
    lines = ['# Architecture Models -- Complete Reference', '']

    # Parent model
    lines.append('## Parent Model: architecture-model-standard')
    lines.append('')
    model = load_model(Path('.architecture-model.yaml'))
    vr = validate_model(model)
    e = model.entities

    lines.append(f'- **Schema Version:** {model.meta.schema_version}')
    lines.append(f'- **Validation Score:** {vr.score}/100')
    lines.append(f'- **Components:** {len(e.components or [])}')
    lines.append(f'- **Capabilities:** {len(e.capabilities or [])}')
    lines.append(f'- **Interfaces:** {len(e.interfaces or [])}')
    lines.append(f'- **Behaviors:** {len(e.behaviors or [])}')
    lines.append(f'- **Constraints:** {len(e.constraints or [])}')
    lines.append(f'- **Layers:** {len(e.layers or [])}')
    lines.append(f'- **Actors:** {len(e.actors or [])}')
    lines.append(f'- **Relationships:** {len(model.relationships or [])}')
    total_sigs = sum(len(c.signatures) for c in e.components if c.signatures)
    total_consts = sum(len(c.constants) for c in e.components if c.constants)
    total_contracts = sum(len(c.test_contracts) for c in e.components if c.test_contracts)
    lines.append(f'- **Signatures:** {total_sigs}')
    lines.append(f'- **Constants:** {total_consts}')
    lines.append(f'- **Test Contracts:** {total_contracts}')
    lines.append('')

    # Actors
    lines.append('### Actors')
    lines.append('')
    for a in (e.actors or []):
        lines.append(f'- **{a.id}** -- {a.name}: {a.description}')
    lines.append('')

    # Capabilities
    lines.append('### Capabilities')
    lines.append('')
    lines.append('| ID | Name | F-Block | Description |')
    lines.append('|----|------|---------|-------------|')
    for c in (e.capabilities or []):
        lines.append(f'| {c.id} | {c.name} | {c.source_block} | {c.description} |')
    lines.append('')

    # Interfaces
    lines.append('### Interfaces')
    lines.append('')
    lines.append('| ID | Name | Type | Description |')
    lines.append('|----|------|------|-------------|')
    for i in (e.interfaces or []):
        itype = getattr(i, 'type', '') or ''
        lines.append(f'| {i.id} | {i.name} | {itype} | {i.description} |')
    lines.append('')

    # Behaviors
    lines.append('### Behaviors')
    lines.append('')
    for b in (e.behaviors or []):
        lines.append(f'- **{b.id}** -- {b.name}: {b.description}')
    lines.append('')

    # Constraints
    lines.append('### Constraints')
    lines.append('')
    for c in (e.constraints or []):
        ctype = getattr(c, 'type', '') or ''
        lines.append(f'- **{c.id}** -- {c.name} ({ctype}): {c.description}')
    lines.append('')

    # Components table
    lines.append('### Components')
    lines.append('')
    lines.append('| ID | Name | F-Block | Sigs | Const | Contracts | Files | Regen |')
    lines.append('|----|------|---------|:----:|:-----:|:---------:|:-----:|:-----:|')
    for c in sorted(e.components, key=lambda x: x.id):
        ns = len(c.signatures) if c.signatures else 0
        nc = len(c.constants) if c.constants else 0
        nt = len(c.test_contracts) if c.test_contracts else 0
        nf = len(c.files) if c.files else 0
        fb = c.source_block or '-'
        regen = 'YES' if nt > 0 and ns > 0 else 'NO'
        lines.append(f'| {c.id} | {c.name} | {fb} | {ns} | {nc} | {nt} | {nf} | {regen} |')
    lines.append('')

    # Component details
    lines.append('### Component Details')
    lines.append('')
    for c in sorted(e.components, key=lambda x: x.id):
        lines.append(f'#### {c.id}: {c.name}')
        lines.append('')
        lines.append(f'- **F-Block:** {c.source_block or "-"}')
        lines.append(f'- **Description:** {c.description or "-"}')
        if c.files:
            lines.append(f'- **Files:** {", ".join(c.files)}')
        lines.append('')

        if c.constants:
            lines.append('**Constants:**')
            lines.append('')
            for k in c.constants:
                ctx = f' ({k.context})' if getattr(k, 'context', None) else ''
                lines.append(f'- `{k.name}` = `{k.value}`{ctx}')
            lines.append('')

        if c.signatures:
            lines.append('**Signatures:**')
            lines.append('')
            for s in c.signatures:
                params = ', '.join(s.params) if s.params else ''
                ret = f' --> {s.returns}' if s.returns else ''
                dec = ''
                if getattr(s, 'decorators', None):
                    dec = f' @{", ".join(s.decorators)}'
                lines.append(f'- `{s.name}({params}){ret}`{dec}')
            lines.append('')

        if c.test_contracts:
            lines.append(f'**Test Contracts ({len(c.test_contracts)}):**')
            lines.append('')
            lines.append('| Test File | Method | Assertion | Type |')
            lines.append('|-----------|--------|-----------|------|')
            for tc in c.test_contracts:
                a = tc.assertion.replace('|', '\\|') if tc.assertion else ''
                if len(a) > 60:
                    a = a[:57] + '...'
                lines.append(f'| {tc.test_file} | {tc.test_method} | {a} | {tc.contract_type} |')
            lines.append('')

    # Relationships
    lines.append('### Relationships')
    lines.append('')
    lines.append('| Type | From | To |')
    lines.append('|------|------|-----|')
    for r in (model.relationships or []):
        rtype = r.type.value if hasattr(r.type, 'value') else str(r.type)
        lines.append(f'| {rtype} | {r.from_id} | {r.to_id} |')
    lines.append('')

    lines.append('\\newpage')
    lines.append('')

    # Sub-models
    for f in sorted(Path('.architecture-models').glob('*/.architecture-model.yaml')):
        m = load_model(f)
        bid = f.parent.name
        me = m.entities
        vr2 = validate_model(m)

        lines.append(f'## Sub-Model {bid}: {m.meta.system}')
        lines.append('')
        lines.append(f'- **Validation Score:** {vr2.score}/100')
        refines = getattr(m.meta, 'refines_component', None)
        if refines:
            lines.append(f'- **Refines:** {refines}')
        lines.append(f'- **Components:** {len(me.components or [])}')
        lines.append(f'- **Capabilities:** {len(me.capabilities or [])}')
        lines.append(f'- **Interfaces:** {len(me.interfaces or [])}')
        lines.append(f'- **Behaviors:** {len(me.behaviors or [])}')
        lines.append(f'- **Constraints:** {len(me.constraints or [])}')
        lines.append(f'- **Relationships:** {len(m.relationships or [])}')
        lines.append('')

        if me.capabilities:
            lines.append('**Capabilities:**')
            lines.append('')
            for c in me.capabilities:
                lines.append(f'- {c.id}: {c.name} (F-Block {c.source_block})')
            lines.append('')

        if me.interfaces:
            lines.append('**Interfaces:**')
            lines.append('')
            for i in me.interfaces:
                lines.append(f'- {i.id}: {i.name}')
            lines.append('')

        if me.behaviors:
            lines.append('**Behaviors:**')
            lines.append('')
            for b in me.behaviors:
                lines.append(f'- {b.id}: {b.name}')
            lines.append('')

        if me.constraints:
            lines.append('**Constraints:**')
            lines.append('')
            for c in me.constraints:
                lines.append(f'- {c.id}: {c.name}')
            lines.append('')

        lines.append('**Components:**')
        lines.append('')
        lines.append('| ID | Name | Sigs | Const | Contracts |')
        lines.append('|----|------|:----:|:-----:|:---------:|')
        for c in (me.components or []):
            ns = len(c.signatures) if c.signatures else 0
            nc = len(c.constants) if c.constants else 0
            nt = len(c.test_contracts) if c.test_contracts else 0
            lines.append(f'| {c.id} | {c.name} | {ns} | {nc} | {nt} |')
        lines.append('')

        lines.append('**Relationships:**')
        lines.append('')
        lines.append('| Type | From | To |')
        lines.append('|------|------|-----|')
        for r in (m.relationships or []):
            rtype = r.type.value if hasattr(r.type, 'value') else str(r.type)
            lines.append(f'| {rtype} | {r.from_id} | {r.to_id} |')
        lines.append('')
        lines.append('\\newpage')
        lines.append('')

    content = '\n'.join(lines)
    Path('output/all-models-reference.md').write_text(content)
    print(f'Generated {len(lines)} lines')


if __name__ == '__main__':
    main()
