# Fill Promise — Attribute Authoring Task

You are authoring the `{attribute}` attribute for architecture entity
`{entity_id}` in a v3 architecture model.

## Human intent (verbatim note)

{note_body}

## Target entity

- **ID:** {entity_id}
- **Kind:** {entity_kind}
- **Name:** {entity_name}
- **Description:** {entity_description}

## Existing promises on target

The line marked `→` is the promise slot you are authoring.

{promises_block}

## Parent chain (via `contains`)

{parent_chain}

## Sibling entities (same parent)

{siblings_block}

## 1-hop relations (outbound)

{relations_block}

## Output

Return a JSON object matching the schema:

```json
{{"content": "<the value to set at entities.{entity_kind_singular}[id={entity_id}].{attribute}>"}}
```

Keep the content concise, factual, and grounded strictly in the human
intent above. Do not invent facts that are not either in the note or in
the surrounding entity context. If the intent is ambiguous, prefer the
more conservative interpretation.
