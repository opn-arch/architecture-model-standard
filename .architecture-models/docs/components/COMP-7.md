# Component: Schema (COMP-7)

**Status:** Status.ACTIVE
**Description:** —

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/profiles/schema.py` | — | — |

## Responsibilities

- from dict
- get extended values

## Relationships

### Dependencies (outgoing)

None

### Dependents (incoming)

None

## Behaviors Realized

None

## Public API

| Function | Parameters | Returns | Description |
|----------|-----------|---------|-------------|
| `load_profile` | `name_or_path: str` | `DomainProfile` |  |
| `from_dict` | `data: dict[str, Any]` | `DomainProfile` |  |
| `get_extended_values` | `enum_name: str` | `list[str]` |  |

## Interface Dependencies

- **provides** `exposes_to_Core` → COMP-4 (Core) [load_profile, EnumExtension, EntityExtension, ConditionalRule, DomainProfile]

## Patterns

None

## Confidence

70%
