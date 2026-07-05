"""Static few-shot examples for oracle extraction prompt.

These hand-crafted examples demonstrate precision and restraint:
- Only create depends-on where actual imports exist
- One component per significant module (>20 LOC)
- Structural relationships (contains, realizes) don't need import backing
"""

from __future__ import annotations

# A manually crafted example showing a 5-file HTTP client library.
# Demonstrates: 4 components, 4 import-backed depends-on edges,
# structural contains/realizes that don't need import evidence.
MANUAL_EXAMPLE = """\
### Source (httpx-lite)
```
httpx_lite/
  __init__.py   (12 LOC, re-exports only)
  client.py     (85 LOC, imports: models, transport, auth)
  models.py     (60 LOC, no internal imports)
  transport.py  (45 LOC, imports: models)
  auth.py       (30 LOC, imports: models)
```

### Correct Output
```yaml
meta:
  schema_version: "1.0"
  project: "httpx-lite"
entities:
  actors:
    - {id: actor-api-consumer, name: API Consumer, status: ACTIVE}
  capabilities:
    - {id: cap-http-requests, name: HTTP Request Handling, status: ACTIVE}
  behaviors:
    - {id: beh-send-request, name: Send HTTP Request, status: ACTIVE}
  interfaces:
    - {id: iface-client-api, name: Client Public API, status: ACTIVE}
  constraints:
    - {id: con-timeout, name: Request Timeout Limit, status: ACTIVE}
  layers:
    - {id: layer-core, name: Core Library, status: ACTIVE}
  components:
    # __init__.py omitted: re-export facade, not a component
    - {id: comp-client, name: client, status: ACTIVE}
    - {id: comp-models, name: models, status: ACTIVE}
    - {id: comp-transport, name: transport, status: ACTIVE}
    - {id: comp-auth, name: auth, status: ACTIVE}
relationships:
  # STRUCTURAL (no import evidence needed):
  - {type: contains, from: layer-core, to: comp-client}
  - {type: contains, from: layer-core, to: comp-models}
  - {type: contains, from: layer-core, to: comp-transport}
  - {type: contains, from: layer-core, to: comp-auth}
  - {type: realizes, from: comp-client, to: cap-http-requests}
  - {type: exposes, from: comp-client, to: iface-client-api}
  # IMPORT-BACKED (each matches a real import statement):
  - {type: depends-on, from: comp-client, to: comp-models}
  - {type: depends-on, from: comp-client, to: comp-transport}
  - {type: depends-on, from: comp-client, to: comp-auth}
  - {type: depends-on, from: comp-transport, to: comp-models}
  # NOT created: auth->transport (no import exists)
```

4 components for 4 files >20 LOC; 4 depends-on for 4 imports; no invented edges.\
"""

# Placeholder for a real extraction example from python-dotenv or similar.
# Will be populated after running the improved prompt on actual repos.
REAL_EXAMPLE = ""
