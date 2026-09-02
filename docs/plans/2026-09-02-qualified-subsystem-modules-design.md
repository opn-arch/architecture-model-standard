# Qualified Subsystem Modules Design

The HTML viewer will build module data as part of the existing submodel loading pass. Each safely resolved child model owns the files explicitly listed by its components. Its modules use keys of the form `<system-key>::module::<normalized-path>`, so identical paths in different child models cannot collide.

For each child model, the loader will try an adjacent `manifest.json`, then `.architecture-models/<slug>/manifest.json`. If neither is valid, it will reuse the root manifest record for each child-owned path. Remaining owned paths become stubs. Manifest records not owned by model components are excluded.

Root module records are restricted to files explicitly owned by root inline components. A child-qualified page is canonical for child-owned files; an explicit root component may independently retain a root page for the same path. Component file links carry resolved module keys rather than guessing from file paths.

All candidate paths must resolve under the repository root. Invalid or escaping submodel and manifest candidates are ignored. Module records retain canonical paths for pipeline-history matching while comments and navigation use qualified storage keys. Existing JSON escaping, inline assets, and DOM text escaping remain the security boundary.

Tests will first establish collisions, fallback stubs, qualified links, traversal rejection, history/comment behavior, JSON/JavaScript validity, no external assets, and hostile-name safety. Focused viewer tests run before the prescribed full suite.
