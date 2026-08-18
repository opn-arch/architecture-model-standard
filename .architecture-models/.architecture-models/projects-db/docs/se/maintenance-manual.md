---
document: Maintenance Manual
system: Projects (db)
system_id: SYS-unknown
generated_at: 2026-08-18T12:32:31Z
generator_version: 0.3.0
model_hash: fcdfcd0d1016
edition: 3
---

# Maintenance Manual: Projects (db)

## Component Inventory

| Component | Kind | Layer | Files | Signatures | Test Contracts |
|-----------|------|-------|-------|-----------|----------------|
| Client (COMP-2) | service | — | 5 | 0 | 0 |
| Creation (COMP-3) | service | — | 5 | 0 | 0 |
| Features (COMP-4) | service | — | 6 | 0 | 0 |
| Introspection (COMP-5) | service | — | 5 | 0 | 0 |
| Operations (COMP-6) | service | — | 5 | 0 | 0 |
| Schema (COMP-7) | service | — | 5 | 0 | 0 |
| Validation (COMP-8) | service | — | 3 | 0 | 0 |
| Ddl References (COMP-9) | service | — | 1 | 0 | 0 |
| Compiler (COMP-10) | service | — | 3 | 0 | 0 |
| Functions (COMP-11) | service | — | 2 | 0 | 0 |
| Autodetector (COMP-12) | service | — | 1 | 0 | 0 |
| Exceptions (COMP-13) | service | — | 1 | 0 | 0 |
| Executor (COMP-14) | service | — | 1 | 0 | 0 |
| Graph (COMP-15) | service | — | 1 | 0 | 0 |
| Loader (COMP-16) | service | — | 1 | 0 | 0 |
| Migration (COMP-17) | service | — | 1 | 0 | 0 |
| Fields (COMP-18) | service | — | 1 | 0 | 0 |
| Models (COMP-19) | service | — | 1 | 0 | 0 |
| Special (COMP-20) | service | — | 1 | 0 | 0 |
| Optimizer (COMP-21) | service | — | 1 | 0 | 0 |
| Questioner (COMP-22) | service | — | 1 | 0 | 0 |
| Recorder (COMP-23) | service | — | 1 | 0 | 0 |
| Serializer (COMP-24) | service | — | 1 | 0 | 0 |
| State (COMP-25) | service | — | 1 | 0 | 0 |
| Writer (COMP-26) | service | — | 1 | 0 | 0 |
| Aggregates (COMP-27) | service | — | 1 | 0 | 0 |
| Constraints (COMP-28) | service | — | 1 | 0 | 0 |
| Deletion (COMP-29) | service | — | 1 | 0 | 0 |
| Enums (COMP-30) | service | — | 1 | 0 | 0 |
| Expressions (COMP-31) | service | — | 1 | 0 | 0 |
| Fetch Modes (COMP-32) | service | — | 1 | 0 | 0 |
| Composite (COMP-33) | service | — | 1 | 0 | 0 |
| Files (COMP-34) | service | — | 1 | 0 | 0 |
| Generated (COMP-35) | service | — | 1 | 0 | 0 |
| Json (COMP-36) | service | — | 2 | 0 | 0 |
| Mixins (COMP-37) | service | — | 2 | 0 | 0 |
| Proxy (COMP-38) | service | — | 1 | 0 | 0 |
| Related (COMP-39) | service | — | 3 | 0 | 0 |
| Related Lookups (COMP-41) | service | — | 1 | 0 | 0 |
| Reverse Related (COMP-42) | service | — | 1 | 0 | 0 |
| Tuple Lookups (COMP-43) | service | — | 1 | 0 | 0 |
| Comparison (COMP-44) | service | — | 1 | 0 | 0 |
| Datetime (COMP-45) | service | — | 1 | 0 | 0 |
| Math (COMP-46) | service | — | 1 | 0 | 0 |
| Text (COMP-47) | service | — | 1 | 0 | 0 |
| Uuid (COMP-48) | service | — | 1 | 0 | 0 |
| Window (COMP-49) | service | — | 1 | 0 | 0 |
| Indexes (COMP-50) | service | — | 1 | 0 | 0 |
| Manager (COMP-52) | service | — | 1 | 0 | 0 |
| Options (COMP-53) | service | — | 1 | 0 | 0 |
| Query (COMP-54) | service | — | 3 | 0 | 0 |
| Query Utils (COMP-55) | service | — | 13 | 0 | 0 |
| Signals (COMP-56) | service | — | 2 | 0 | 0 |
| Datastructures (COMP-57) | service | — | 1 | 0 | 0 |
| Subqueries (COMP-58) | service | — | 1 | 0 | 0 |
| Where (COMP-59) | service | — | 1 | 0 | 0 |
| Transaction (COMP-60) | service | — | 1 | 0 | 0 |
| Infrastructure (COMP-62) | service | — | 3 | 0 | 0 |

## Dependency Impact Analysis

| Component | Depends On (fan-out) | Depended By (fan-in) | Impact Risk |
|-----------|---------------------|---------------------|-------------|
| Client | Transaction, Schema, Query Utils, Introspection, Ddl References, Validation, Signals, Creation, Features, Operations | Schema, Special, Operations, Creation, Models, Fields, Questioner, Files, Introspection, Features, Query Utils, Validation, Serializer | HIGH |
| Creation | Infrastructure, Query, Subqueries, Features, Client, Operations, Ddl References, Where, Transaction, Schema, Query Utils, Introspection, Compiler, Datastructures, Validation, Exceptions, Functions, Signals | Questioner, Files, Introspection, Query Utils, Validation, Serializer, Schema, Special, Operations, Features, Client, Models, Fields | HIGH |
| Features | Where, Transaction, Schema, Query Utils, Introspection, Compiler, Datastructures, Ddl References, Validation, Functions, Signals, Infrastructure, Query, Subqueries, Creation, Client, Operations | Creation, Questioner, Models, Fields, Validation, Files, Special, Operations, Introspection, Client, Query Utils, Serializer, Schema | HIGH |
| Introspection | Constraints, Ddl References, Where, Options, Query Utils, Compiler, Datastructures, Infrastructure, Manager, Query, Subqueries, Validation, Creation, Indexes, Models, Related Lookups, Functions, Signals, Aggregates, Features, Transaction, Client, Schema, Expressions, Operations, Fetch Modes, Enums, Deletion | Validation, Schema, Files, Special, Operations, Features, Client, Serializer, Models, Creation, Questioner, Fields, Query Utils | HIGH |
| Operations | Transaction, Client, Schema, Expressions, Query Utils, Introspection, Tuple Lookups, Window, Enums, Generated, Datastructures, Datetime, Constraints, Manager, Json, Ddl References, Text, Validation, Exceptions, Math, Where, Options, Indexes, Proxy, Models, Related Lookups, Functions, Compiler, Mixins, Composite, Signals, Reverse Related, Infrastructure, Query, Subqueries, Creation, Features, Uuid, Special, Files, Comparison, Fetch Modes, Related, Fields, Deletion, Aggregates | Schema, Special, Creation, Models, Fields, Autodetector, Questioner, Validation, Files, Introspection, Features, Client, Query Utils, Serializer | HIGH |
| Schema | Client, Files, Expressions, Operations, Introspection, Fetch Modes, Enums, Related, Fields, Deletion, Datetime, Constraints, Ddl References, Where, Options, Proxy, Query Utils, Tuple Lookups, Generated, Compiler, Datastructures, Reverse Related, Infrastructure, Manager, Query, Json, Subqueries, Validation, Exceptions, Creation, Indexes, Models, Related Lookups, Mixins, Composite, Signals, Aggregates, Features, Transaction | Special, Operations, Features, Client, Models, Creation, Questioner, Fields, Files, Introspection, Query Utils, Validation, Serializer | HIGH |
| Validation | Introspection, Ddl References, Signals, Creation, Features, Operations, Transaction, Client, Schema, Query Utils | Files, Special, Operations, Introspection, Features, Client, Query Utils, Serializer, Schema, Models, Creation, Questioner, Fields | HIGH |
| Ddl References | — | Introspection, Query Utils, Validation, Schema, Operations, Features, Creation, Client, Functions, Indexes, Related | HIGH |
| Compiler | Fields, Deletion, Datetime, Where, Transaction, Proxy, Query Utils, Tuple Lookups, Enums, Generated, Datastructures, Reverse Related, Constraints, Manager, Json, Text, Exceptions, Math, Options, Indexes, Models, Related Lookups, Functions, Mixins, Composite, Signals, Infrastructure, Query, Subqueries, Aggregates, Uuid, Files, Expressions, Comparison, Fetch Modes, Window, Related | Generated, Subqueries, Datastructures, Introspection, Features, Query Utils, Schema, Operations, Query, Creation, Tuple Lookups, Indexes, Constraints | HIGH |
| Functions | Signals, Aggregates, Transaction, Uuid, Expressions, Fetch Modes, Enums, Deletion, Datetime, Ddl References, Options, Query Utils, Infrastructure, Constraints, Manager, Query, Math, Indexes, Models, Related Lookups | Indexes, Mixins, Text, Related, Constraints, Where, Operations, Query, Introspection, Features, Compiler, Query Utils, Math, Json, Creation, Aggregates | HIGH |
| Autodetector | Serializer, Questioner, Optimizer, Options, Indexes, Models, Related Lookups, Signals, Infrastructure, Query, State, Executor, Special, Expressions, Operations, Fetch Modes, Loader, Fields, Deletion, Aggregates, Graph, Transaction, Migration, Query Utils, Recorder, Enums, Writer, Constraints, Manager, Exceptions | Graph, State, Loader, Serializer, Migration, Models, Fields, Writer | HIGH |
| Exceptions | Transaction, Query Utils | Where, Loader, Recorder, Subqueries, Files, Fetch Modes, Graph, Operations, Query, State, Compiler, Query Utils, Executor, Serializer, Schema, Expressions, Migration, Creation, Tuple Lookups, Aggregates, Related Lookups, Models, Fields, Options, Writer, Related, Constraints, Datastructures, Autodetector | HIGH |
| Executor | Loader, Transaction, Query Utils, Recorder, Exceptions, State | Fields, Writer, Autodetector, Loader, Graph, State, Serializer, Models, Migration | HIGH |
| Graph | Migration, Autodetector, Query Utils, Recorder, Datastructures, Exceptions, Serializer, Questioner, Optimizer, Writer, Executor, Loader, State, Transaction | Loader, Serializer, State, Models, Migration, Autodetector, Fields, Writer | HIGH |
| Loader | Graph, Exceptions, Serializer, Questioner, Autodetector, Query Utils, Writer, Executor, Optimizer, State, Transaction, Migration, Recorder | Executor, Serializer, Migration, Models, Fields, Writer, Autodetector, Questioner, Graph, State | HIGH |
| Migration | Loader, Transaction, Autodetector, Query Utils, Recorder, Writer, Graph, Exceptions, Serializer, Questioner, Optimizer, State, Executor | Graph, State, Serializer, Models, Fields, Writer, Autodetector, Loader | HIGH |
| Fields | Models, Related Lookups, Signals, Infrastructure, Query, Executor, Features, Client, Expressions, Operations, Fetch Modes, Loader, Deletion, State, Aggregates, Transaction, Migration, Autodetector, Schema, Query Utils, Introspection, Recorder, Enums, Writer, Constraints, Manager, Validation, Graph, Exceptions, Serializer, Questioner, Creation, Optimizer, Options, Indexes | Compiler, Query Utils, Serializer, Schema, Window, Aggregates, Mixins, Models, Options, Uuid, Text, Constraints, Autodetector, Math, Json, Datetime, Related Lookups, Files, Related, Operations, Query, Composite, State | HIGH |
| Models | Files, Mixins, Composite, Deletion, State, Aggregates, Features, Transaction, Migration, Special, Client, Schema, Expressions, Operations, Introspection, Recorder, Fetch Modes, Loader, Tuple Lookups, Enums, Related, Fields, Constraints, Manager, Json, Validation, Graph, Serializer, Options, Proxy, Autodetector, Related Lookups, Query Utils, Generated, Signals, Writer, Reverse Related, Infrastructure, Query, Executor, Exceptions, Questioner, Creation, Optimizer, Indexes | Related Lookups, Mixins, Fields, Options, Uuid, Comparison, Text, Related, Constraints, Datastructures, Autodetector, Where, Deletion, Datetime, Subqueries, Files, Operations, Query, Introspection, Window, Composite, State, Compiler, Query Utils, Proxy, Signals, Serializer, Schema, Expressions, Math, Json, Tuple Lookups, Aggregates, Questioner, Generated, Functions, Indexes, Manager | HIGH |
| Special | Client, Schema, Operations, Introspection, Validation, Query Utils, Creation, Features, Transaction | Models, Autodetector, Operations, Query Utils, Serializer | HIGH |
| Optimizer | — | Writer, Autodetector, Graph, State, Loader, Serializer, Migration, Models, Fields | HIGH |
| Questioner | Signals, Infrastructure, Query, Creation, Features, Indexes, Deletion, Aggregates, Transaction, Client, Schema, Expressions, Operations, Introspection, Fetch Modes, Loader, Enums, Datetime, Constraints, Manager, Validation, Options, Models, Related Lookups, Query Utils | Writer, Autodetector, Loader, Graph, State, Serializer, Migration, Models, Fields | HIGH |
| Recorder | Exceptions, Transaction, Query Utils | Graph, State, Executor, Serializer, Models, Migration, Fields, Writer, Autodetector, Loader | HIGH |
| Serializer | Fetch Modes, Loader, Fields, Deletion, Datetime, Graph, Transaction, Migration, Autodetector, Query Utils, Introspection, Recorder, Enums, Writer, Constraints, Manager, Validation, Exceptions, Math, Questioner, Creation, Optimizer, Options, Indexes, Models, Related Lookups, Signals, Infrastructure, Query, State, Aggregates, Executor, Features, Uuid, Special, Client, Schema, Expressions, Operations | Autodetector, Loader, Graph, State, Models, Migration, Fields, Writer | HIGH |
| State | Deletion, Aggregates, Transaction, Migration, Autodetector, Expressions, Recorder, Fetch Modes, Tuple Lookups, Enums, Generated, Constraints, Manager, Json, Text, Graph, Exceptions, Serializer, Questioner, Optimizer, Options, Indexes, Proxy, Models, Related Lookups, Query Utils, Mixins, Composite, Signals, Writer, Reverse Related, Infrastructure, Query, Executor, Files, Loader, Related, Fields | Models, Autodetector, Fields, Writer, Loader, Executor, Serializer, Graph, Migration | HIGH |
| Writer | Questioner, Optimizer, Executor, Loader, State, Transaction, Migration, Autodetector, Query Utils, Recorder, Graph, Exceptions, Serializer | Loader, Serializer, Graph, Migration, State, Models, Fields, Autodetector | HIGH |
| Aggregates | Composite, Signals, Transaction, Uuid, Files, Expressions, Comparison, Fetch Modes, Window, Enums, Related, Fields, Deletion, Datetime, Constraints, Options, Proxy, Query Utils, Tuple Lookups, Generated, Reverse Related, Infrastructure, Manager, Query, Json, Text, Exceptions, Math, Indexes, Models, Related Lookups, Functions, Mixins | Query, Window, State, Tuple Lookups, Functions, Signals, Manager, Models, Uuid, Comparison, Expressions, Constraints, Math, Json, Questioner, Generated, Indexes, Subqueries, Related Lookups, Mixins, Fields, Files, Options, Text, Related, Datastructures, Autodetector, Introspection, Where, Composite, Deletion, Compiler, Query Utils, Proxy, Datetime, Serializer, Schema, Operations | HIGH |
| Constraints | Math, Indexes, Models, Related Lookups, Functions, Mixins, Composite, Signals, Aggregates, Transaction, Uuid, Files, Expressions, Comparison, Fetch Modes, Window, Enums, Related, Fields, Deletion, Datetime, Where, Options, Proxy, Query Utils, Tuple Lookups, Generated, Compiler, Datastructures, Reverse Related, Infrastructure, Manager, Query, Json, Text, Subqueries, Exceptions | Introspection, Where, Composite, Deletion, Query Utils, Proxy, Datetime, Schema, Files, Operations, Query, Window, State, Tuple Lookups, Compiler, Aggregates, Signals, Serializer, Models, Expressions, Math, Json, Questioner, Generated, Functions, Indexes, Manager, Subqueries, Related Lookups, Mixins, Fields, Options, Uuid, Comparison, Text, Related, Datastructures, Autodetector | HIGH |
| Deletion | Constraints, Manager, Options, Indexes, Models, Related Lookups, Signals, Infrastructure, Query, Fetch Modes, Aggregates, Transaction, Expressions, Query Utils, Enums | Window, Composite, State, Compiler, Query Utils, Proxy, Signals, Serializer, Schema, Models, Expressions, Math, Json, Tuple Lookups, Aggregates, Questioner, Generated, Functions, Indexes, Manager, Related Lookups, Mixins, Fields, Options, Uuid, Comparison, Text, Related, Constraints, Datastructures, Autodetector, Where, Datetime, Subqueries, Files, Operations, Query, Introspection | HIGH |
| Enums | Query Utils | Proxy, Datetime, Schema, Files, Operations, Query, Window, State, Tuple Lookups, Compiler, Aggregates, Functions, Signals, Serializer, Models, Expressions, Constraints, Math, Json, Questioner, Generated, Indexes, Manager, Subqueries, Related Lookups, Mixins, Fields, Options, Uuid, Comparison, Text, Related, Datastructures, Autodetector, Introspection, Where, Composite, Deletion, Query Utils | HIGH |
| Expressions | Uuid, Fetch Modes, Deletion, Datetime, Aggregates, Transaction, Query Utils, Enums, Constraints, Manager, Exceptions, Options, Indexes, Models, Related Lookups, Signals, Infrastructure, Query | Schema, Operations, Query, Window, State, Tuple Lookups, Aggregates, Functions, Indexes, Signals, Manager, Models, Fields, Uuid, Comparison, Text, Constraints, Autodetector, Math, Json, Questioner, Generated, Datetime, Subqueries, Related Lookups, Mixins, Files, Options, Related, Datastructures, Introspection, Where, Composite, Deletion, Compiler, Query Utils, Proxy, Serializer | HIGH |
| Fetch Modes | Exceptions | Serializer, Schema, Expressions, Query, Window, State, Tuple Lookups, Aggregates, Functions, Indexes, Signals, Manager, Models, Fields, Options, Uuid, Comparison, Text, Constraints, Autodetector, Math, Json, Deletion, Questioner, Generated, Datetime, Subqueries, Related Lookups, Mixins, Files, Related, Datastructures, Operations, Introspection, Where, Composite, Compiler, Query Utils, Proxy | HIGH |
| Composite | Deletion, Constraints, Json, Options, Proxy, Query Utils, Tuple Lookups, Generated, Reverse Related, Infrastructure, Manager, Query, Indexes, Models, Related Lookups, Mixins, Signals, Aggregates, Transaction, Files, Expressions, Fetch Modes, Enums, Related, Fields | Aggregates, Related Lookups, Mixins, Models, Options, Uuid, Text, Related, Constraints, Datetime, Files, Operations, Query, State, Compiler, Query Utils, Schema, Math, Json, Window | HIGH |
| Files | Query Utils, Introspection, Tuple Lookups, Enums, Generated, Reverse Related, Constraints, Manager, Json, Validation, Exceptions, Creation, Options, Indexes, Models, Related Lookups, Mixins, Composite, Signals, Infrastructure, Query, Aggregates, Features, Client, Schema, Expressions, Operations, Fetch Modes, Related, Fields, Deletion, Datetime, Transaction, Proxy | Schema, Models, Math, Json, Aggregates, Related Lookups, Mixins, Options, Uuid, Text, Related, Constraints, Datetime, Operations, Query, Window, Composite, State, Compiler, Query Utils | HIGH |
| Generated | Compiler, Datastructures, Signals, Infrastructure, Query, Subqueries, Deletion, Aggregates, Transaction, Expressions, Fetch Modes, Enums, Constraints, Manager, Where, Options, Indexes, Models, Related Lookups, Query Utils | Datetime, Files, Related, Operations, Query, Composite, State, Compiler, Query Utils, Schema, Math, Json, Window, Aggregates, Related Lookups, Mixins, Models, Options, Uuid, Text, Constraints | HIGH |
| Json | Query, Text, Math, Uuid, Files, Comparison, Related, Deletion, Aggregates, Transaction, Expressions, Fetch Modes, Tuple Lookups, Window, Enums, Fields, Generated, Datetime, Constraints, Manager, Options, Indexes, Proxy, Models, Related Lookups, Query Utils, Functions, Mixins, Composite, Signals, Reverse Related, Infrastructure | Where, Composite, Datetime, Files, Operations, Query, Window, State, Compiler, Query Utils, Schema, Models, Math, Aggregates, Indexes, Related Lookups, Mixins, Options, Uuid, Text, Related, Constraints | HIGH |
| Mixins | Models, Related Lookups, Query Utils, Functions, Composite, Signals, Reverse Related, Infrastructure, Query, Uuid, Files, Comparison, Related, Fields, Deletion, Aggregates, Transaction, Expressions, Fetch Modes, Tuple Lookups, Window, Enums, Generated, Datetime, Constraints, Manager, Json, Text, Math, Options, Indexes, Proxy | Indexes, Models, Options, Uuid, Text, Constraints, Where, Datetime, Related Lookups, Files, Reverse Related, Related, Operations, Query, Composite, State, Compiler, Query Utils, Schema, Math, Json, Window, Aggregates | HIGH |
| Proxy | Enums, Deletion, Constraints, Options, Query Utils, Infrastructure, Manager, Query, Indexes, Models, Related Lookups, Signals, Aggregates, Transaction, Expressions, Fetch Modes | Options, Related, Composite, Compiler, Query Utils, Schema, Operations, Query, Window, State, Aggregates, Models, Uuid, Text, Constraints, Math, Json, Datetime, Related Lookups, Mixins, Files | HIGH |
| Related | Options, Proxy, Models, Related Lookups, Query Utils, Functions, Generated, Composite, Signals, Reverse Related, Infrastructure, Query, Text, Math, Indexes, Uuid, Files, Mixins, Deletion, Aggregates, Transaction, Expressions, Comparison, Fetch Modes, Tuple Lookups, Window, Enums, Fields, Datetime, Constraints, Manager, Json, Ddl References, Exceptions | Schema, Math, Json, Window, Aggregates, Mixins, Models, Options, Uuid, Text, Constraints, Datetime, Related Lookups, Files, Operations, Query, Composite, State, Compiler, Query Utils | HIGH |
| Related Lookups | Models, Query Utils, Datastructures, Composite, Signals, Reverse Related, Infrastructure, Query, Math, Files, Mixins, Deletion, Aggregates, Transaction, Expressions, Fetch Modes, Tuple Lookups, Enums, Related, Fields, Generated, Constraints, Manager, Json, Exceptions, Options, Indexes, Proxy | Mixins, Fields, Options, Uuid, Comparison, Text, Related, Constraints, Datastructures, Autodetector, Where, Deletion, Datetime, Subqueries, Files, Operations, Query, Introspection, Window, Composite, State, Compiler, Query Utils, Proxy, Signals, Serializer, Schema, Models, Expressions, Math, Json, Tuple Lookups, Aggregates, Questioner, Generated, Functions, Indexes, Manager | HIGH |
| Reverse Related | Query Utils, Mixins | Datetime, Related Lookups, Mixins, Files, Options, Text, Related, Composite, Compiler, Query Utils, Schema, Operations, Query, Window, State, Aggregates, Models, Uuid, Constraints, Math, Json | HIGH |
| Tuple Lookups | Aggregates, Transaction, Expressions, Fetch Modes, Enums, Deletion, Constraints, Where, Options, Query Utils, Compiler, Datastructures, Infrastructure, Manager, Query, Subqueries, Exceptions, Indexes, Models, Related Lookups, Signals | Datetime, Files, Operations, Query, Window, Composite, State, Compiler, Query Utils, Schema, Models, Math, Json, Aggregates, Related Lookups, Mixins, Options, Uuid, Text, Related, Constraints | HIGH |
| Comparison | Options, Indexes, Models, Related Lookups, Signals, Aggregates, Transaction, Expressions, Fetch Modes, Deletion, Query Utils, Enums, Infrastructure, Constraints, Manager, Query | Math, Json, Aggregates, Indexes, Mixins, Text, Constraints, Where, Related, Operations, Query, Compiler, Query Utils | HIGH |
| Datetime | Tuple Lookups, Enums, Generated, Reverse Related, Constraints, Manager, Json, Options, Indexes, Models, Related Lookups, Mixins, Composite, Signals, Infrastructure, Query, Files, Expressions, Fetch Modes, Related, Fields, Deletion, Aggregates, Transaction, Proxy, Query Utils | Where, Compiler, Query Utils, Serializer, Schema, Expressions, Operations, Query, Aggregates, Functions, Indexes, Text, Constraints, Math, Json, Questioner, Mixins, Files, Related | HIGH |
| Math | Text, Uuid, Files, Comparison, Related, Deletion, Aggregates, Transaction, Expressions, Fetch Modes, Tuple Lookups, Window, Enums, Fields, Generated, Datetime, Constraints, Manager, Json, Options, Indexes, Proxy, Models, Related Lookups, Query Utils, Functions, Mixins, Composite, Signals, Reverse Related, Infrastructure, Query | Constraints, Json, Related Lookups, Related, Operations, Query, Where, Compiler, Query Utils, Serializer, Aggregates, Functions, Indexes, Mixins, Text | HIGH |
| Text | Options, Indexes, Models, Related Lookups, Functions, Mixins, Composite, Signals, Reverse Related, Infrastructure, Query, Uuid, Files, Expressions, Comparison, Fetch Modes, Related, Fields, Deletion, Datetime, Aggregates, Transaction, Proxy, Query Utils, Tuple Lookups, Window, Enums, Generated, Constraints, Manager, Json, Math | Math, Json, Related, Operations, Query, Where, State, Compiler, Query Utils, Transaction, Aggregates, Indexes, Mixins, Options, Constraints | HIGH |
| Uuid | Models, Related Lookups, Mixins, Composite, Signals, Aggregates, Transaction, Files, Expressions, Fetch Modes, Related, Fields, Deletion, Proxy, Query Utils, Tuple Lookups, Enums, Generated, Reverse Related, Infrastructure, Constraints, Manager, Query, Json, Options, Indexes | Expressions, Math, Json, Aggregates, Functions, Indexes, Mixins, Text, Related, Constraints, Where, Operations, Query, Compiler, Query Utils, Serializer | HIGH |
| Window | Deletion, Aggregates, Transaction, Expressions, Fetch Modes, Tuple Lookups, Enums, Related, Fields, Constraints, Manager, Json, Options, Proxy, Models, Related Lookups, Query Utils, Generated, Signals, Reverse Related, Infrastructure, Query, Indexes, Files, Mixins, Composite | Operations, Query, Aggregates, Constraints, Math, Json, Indexes, Mixins, Text, Related, Where, Compiler, Query Utils | HIGH |
| Indexes | Functions, Mixins, Signals, Infrastructure, Query, Subqueries, Uuid, Expressions, Comparison, Fetch Modes, Deletion, Datetime, Aggregates, Where, Transaction, Query Utils, Window, Enums, Compiler, Datastructures, Constraints, Manager, Json, Ddl References, Text, Math, Options, Models, Related Lookups | Comparison, Text, Constraints, Datastructures, Autodetector, Where, Deletion, Questioner, Datetime, Subqueries, Files, Related, Operations, Query, Introspection, Composite, State, Compiler, Query Utils, Proxy, Serializer, Schema, Expressions, Math, Json, Window, Tuple Lookups, Aggregates, Generated, Functions, Signals, Manager, Related Lookups, Mixins, Models, Fields, Options, Uuid | HIGH |
| Manager | Signals, Aggregates, Transaction, Expressions, Fetch Modes, Deletion, Query Utils, Enums, Infrastructure, Constraints, Query, Options, Indexes, Models, Related Lookups | Where, Deletion, Datetime, Subqueries, Files, Operations, Query, Introspection, Window, Composite, State, Compiler, Query Utils, Proxy, Serializer, Schema, Models, Expressions, Math, Json, Tuple Lookups, Aggregates, Questioner, Generated, Functions, Indexes, Signals, Related Lookups, Mixins, Fields, Options, Uuid, Comparison, Text, Related, Constraints, Datastructures, Autodetector | HIGH |
| Options | Proxy, Models, Related Lookups, Mixins, Composite, Signals, Reverse Related, Infrastructure, Query, Files, Fetch Modes, Related, Fields, Deletion, Aggregates, Transaction, Expressions, Query Utils, Tuple Lookups, Enums, Generated, Datastructures, Constraints, Manager, Json, Text, Exceptions, Indexes | Comparison, Text, Related, Datastructures, Autodetector, Introspection, Where, Composite, Deletion, Query Utils, Proxy, Datetime, Schema, Files, Operations, Query, Window, State, Tuple Lookups, Compiler, Aggregates, Functions, Signals, Serializer, Models, Expressions, Constraints, Math, Json, Questioner, Generated, Indexes, Manager, Subqueries, Related Lookups, Mixins, Fields, Uuid | HIGH |
| Query | Aggregates, Transaction, Expressions, Fetch Modes, Tuple Lookups, Window, Enums, Generated, Datetime, Constraints, Manager, Json, Text, Exceptions, Math, Where, Options, Indexes, Proxy, Models, Related Lookups, Query Utils, Functions, Compiler, Mixins, Datastructures, Composite, Signals, Reverse Related, Infrastructure, Subqueries, Uuid, Files, Comparison, Related, Fields, Deletion | Json, Creation, Questioner, Generated, Indexes, Subqueries, Related Lookups, Mixins, Fields, Options, Text, Related, Datastructures, Autodetector, Introspection, Where, Composite, Deletion, Query Utils, Proxy, Datetime, Schema, Files, Operations, Features, Window, State, Tuple Lookups, Compiler, Aggregates, Functions, Signals, Serializer, Manager, Models, Uuid, Comparison, Expressions, Constraints, Math | HIGH |
| Query Utils | Fields, Deletion, Datetime, Constraints, Ddl References, Where, Options, Proxy, Tuple Lookups, Generated, Compiler, Datastructures, Reverse Related, Infrastructure, Manager, Query, Json, Text, Subqueries, Validation, Exceptions, Math, Creation, Indexes, Models, Related Lookups, Functions, Mixins, Composite, Signals, Aggregates, Features, Transaction, Uuid, Special, Client, Files, Schema, Expressions, Operations, Introspection, Comparison, Fetch Modes, Window, Enums, Related | Subqueries, Related Lookups, Mixins, Files, Reverse Related, Graph, Related, Datastructures, Operations, Introspection, Features, Where, Composite, Loader, Compiler, Client, Proxy, Executor, Serializer, Schema, Special, Expressions, Migration, Query, Window, Creation, State, Tuple Lookups, Transaction, Aggregates, Functions, Indexes, Signals, Manager, Models, Fields, Options, Uuid, Comparison, Text, Writer, Constraints, Autodetector, Math, Json, Deletion, Questioner, Enums, Generated, Recorder, Exceptions, Datetime, Validation | HIGH |
| Signals | Deletion, Aggregates, Transaction, Expressions, Fetch Modes, Enums, Constraints, Options, Models, Related Lookups, Query Utils, Infrastructure, Manager, Query, Indexes | Aggregates, Questioner, Generated, Functions, Indexes, Manager, Related Lookups, Mixins, Fields, Options, Uuid, Comparison, Text, Related, Constraints, Datastructures, Autodetector, Where, Deletion, Datetime, Validation, Subqueries, Files, Operations, Query, Introspection, Features, Window, Composite, State, Compiler, Client, Query Utils, Proxy, Serializer, Schema, Models, Expressions, Math, Json, Creation, Tuple Lookups | HIGH |
| Datastructures | Where, Options, Indexes, Models, Related Lookups, Query Utils, Compiler, Signals, Infrastructure, Query, Subqueries, Deletion, Aggregates, Transaction, Expressions, Fetch Modes, Enums, Constraints, Manager, Exceptions | Generated, Subqueries, Related Lookups, Graph, Operations, Introspection, Features, Compiler, Query Utils, Schema, Query, Creation, Tuple Lookups, Indexes, Options, Constraints | HIGH |
| Subqueries | Query Utils, Compiler, Datastructures, Infrastructure, Manager, Query, Exceptions, Indexes, Models, Related Lookups, Signals, Aggregates, Transaction, Expressions, Fetch Modes, Enums, Deletion, Constraints, Where, Options | Creation, Generated, Indexes, Datastructures, Introspection, Query Utils, Schema, Operations, Query, Features, Tuple Lookups, Compiler, Constraints | HIGH |
| Where | Datetime, Constraints, Manager, Json, Exceptions, Options, Indexes, Models, Related Lookups, Query Utils, Functions, Mixins, Signals, Infrastructure, Query, Text, Math, Uuid, Comparison, Deletion, Aggregates, Transaction, Expressions, Fetch Modes, Window, Enums | Datastructures, Introspection, Features, Compiler, Query Utils, Schema, Operations, Query, Creation, Tuple Lookups, Indexes, Constraints, Generated, Subqueries | HIGH |
| Transaction | Query Utils, Text | Operations, Query, Features, Window, State, Tuple Lookups, Compiler, Client, Aggregates, Executor, Functions, Signals, Serializer, Manager, Models, Uuid, Comparison, Expressions, Migration, Constraints, Math, Json, Creation, Questioner, Generated, Recorder, Exceptions, Indexes, Subqueries, Related Lookups, Mixins, Fields, Options, Text, Writer, Related, Datastructures, Autodetector, Introspection, Where, Composite, Deletion, Loader, Query Utils, Proxy, Datetime, Validation, Schema, Files, Special, Graph | HIGH |
| Infrastructure | — | Creation, Questioner, Generated, Indexes, Subqueries, Related Lookups, Mixins, Fields, Options, Text, Related, Datastructures, Autodetector, Introspection, Where, Composite, Deletion, Query Utils, Proxy, Datetime, Schema, Files, Operations, Query, Features, Window, State, Tuple Lookups, Compiler, Aggregates, Functions, Signals, Serializer, Manager, Models, Uuid, Comparison, Expressions, Constraints, Math, Json | HIGH |

## Modification Procedures

For each component, the following files and dependencies must be considered:

### Client (COMP-2)

**Files:**
- `projects/django/django/db/backends/base/client.py`
- `projects/django/django/db/backends/mysql/client.py`
- `projects/django/django/db/backends/oracle/client.py`
- `projects/django/django/db/backends/postgresql/client.py`
- `projects/django/django/db/backends/sqlite3/client.py`
**Downstream dependents (must re-test):** Schema, Special, Operations, Creation, Models, Fields, Questioner, Files, Introspection, Features, Query Utils, Validation, Serializer

### Creation (COMP-3)

**Files:**
- `projects/django/django/db/backends/base/creation.py`
- `projects/django/django/db/backends/mysql/creation.py`
- `projects/django/django/db/backends/oracle/creation.py`
- `projects/django/django/db/backends/postgresql/creation.py`
- `projects/django/django/db/backends/sqlite3/creation.py`
**Downstream dependents (must re-test):** Questioner, Files, Introspection, Query Utils, Validation, Serializer, Schema, Special, Operations, Features, Client, Models, Fields

### Features (COMP-4)

**Files:**
- `projects/django/django/db/backends/base/features.py`
- `projects/django/django/db/backends/dummy/features.py`
- `projects/django/django/db/backends/mysql/features.py`
- `projects/django/django/db/backends/oracle/features.py`
- `projects/django/django/db/backends/postgresql/features.py`
- `projects/django/django/db/backends/sqlite3/features.py`
**Downstream dependents (must re-test):** Creation, Questioner, Models, Fields, Validation, Files, Special, Operations, Introspection, Client, Query Utils, Serializer, Schema

### Introspection (COMP-5)

**Files:**
- `projects/django/django/db/backends/base/introspection.py`
- `projects/django/django/db/backends/mysql/introspection.py`
- `projects/django/django/db/backends/oracle/introspection.py`
- `projects/django/django/db/backends/postgresql/introspection.py`
- `projects/django/django/db/backends/sqlite3/introspection.py`
**Downstream dependents (must re-test):** Validation, Schema, Files, Special, Operations, Features, Client, Serializer, Models, Creation, Questioner, Fields, Query Utils

### Operations (COMP-6)

**Files:**
- `projects/django/django/db/backends/base/operations.py`
- `projects/django/django/db/backends/mysql/operations.py`
- `projects/django/django/db/backends/oracle/operations.py`
- `projects/django/django/db/backends/postgresql/operations.py`
- `projects/django/django/db/backends/sqlite3/operations.py`
**Downstream dependents (must re-test):** Schema, Special, Creation, Models, Fields, Autodetector, Questioner, Validation, Files, Introspection, Features, Client, Query Utils, Serializer

### Schema (COMP-7)

**Files:**
- `projects/django/django/db/backends/base/schema.py`
- `projects/django/django/db/backends/mysql/schema.py`
- `projects/django/django/db/backends/oracle/schema.py`
- `projects/django/django/db/backends/postgresql/schema.py`
- `projects/django/django/db/backends/sqlite3/schema.py`
**Downstream dependents (must re-test):** Special, Operations, Features, Client, Models, Creation, Questioner, Fields, Files, Introspection, Query Utils, Validation, Serializer

### Validation (COMP-8)

**Files:**
- `projects/django/django/db/backends/base/validation.py`
- `projects/django/django/db/backends/mysql/validation.py`
- `projects/django/django/db/backends/oracle/validation.py`
**Downstream dependents (must re-test):** Files, Special, Operations, Introspection, Features, Client, Query Utils, Serializer, Schema, Models, Creation, Questioner, Fields

### Ddl References (COMP-9)

**Files:**
- `projects/django/django/db/backends/ddl_references.py`
**Downstream dependents (must re-test):** Introspection, Query Utils, Validation, Schema, Operations, Features, Creation, Client, Functions, Indexes, Related

### Compiler (COMP-10)

**Files:**
- `projects/django/django/db/backends/mysql/compiler.py`
- `projects/django/django/db/backends/postgresql/compiler.py`
- `projects/django/django/db/models/sql/compiler.py`
**Downstream dependents (must re-test):** Generated, Subqueries, Datastructures, Introspection, Features, Query Utils, Schema, Operations, Query, Creation, Tuple Lookups, Indexes, Constraints

### Functions (COMP-11)

**Files:**
- `projects/django/django/db/backends/oracle/functions.py`
- `projects/django/django/db/backends/sqlite3/_functions.py`
**Downstream dependents (must re-test):** Indexes, Mixins, Text, Related, Constraints, Where, Operations, Query, Introspection, Features, Compiler, Query Utils, Math, Json, Creation, Aggregates

### Autodetector (COMP-12)

**Files:**
- `projects/django/django/db/migrations/autodetector.py`
**Downstream dependents (must re-test):** Graph, State, Loader, Serializer, Migration, Models, Fields, Writer

### Exceptions (COMP-13)

**Files:**
- `projects/django/django/db/migrations/exceptions.py`
**Downstream dependents (must re-test):** Where, Loader, Recorder, Subqueries, Files, Fetch Modes, Graph, Operations, Query, State, Compiler, Query Utils, Executor, Serializer, Schema, Expressions, Migration, Creation, Tuple Lookups, Aggregates, Related Lookups, Models, Fields, Options, Writer, Related, Constraints, Datastructures, Autodetector

### Executor (COMP-14)

**Files:**
- `projects/django/django/db/migrations/executor.py`
**Downstream dependents (must re-test):** Fields, Writer, Autodetector, Loader, Graph, State, Serializer, Models, Migration

### Graph (COMP-15)

**Files:**
- `projects/django/django/db/migrations/graph.py`
**Downstream dependents (must re-test):** Loader, Serializer, State, Models, Migration, Autodetector, Fields, Writer

### Loader (COMP-16)

**Files:**
- `projects/django/django/db/migrations/loader.py`
**Downstream dependents (must re-test):** Executor, Serializer, Migration, Models, Fields, Writer, Autodetector, Questioner, Graph, State

### Migration (COMP-17)

**Files:**
- `projects/django/django/db/migrations/migration.py`
**Downstream dependents (must re-test):** Graph, State, Serializer, Models, Fields, Writer, Autodetector, Loader

### Fields (COMP-18)

**Files:**
- `projects/django/django/db/migrations/operations/fields.py`
**Downstream dependents (must re-test):** Compiler, Query Utils, Serializer, Schema, Window, Aggregates, Mixins, Models, Options, Uuid, Text, Constraints, Autodetector, Math, Json, Datetime, Related Lookups, Files, Related, Operations, Query, Composite, State

### Models (COMP-19)

**Files:**
- `projects/django/django/db/migrations/operations/models.py`
**Downstream dependents (must re-test):** Related Lookups, Mixins, Fields, Options, Uuid, Comparison, Text, Related, Constraints, Datastructures, Autodetector, Where, Deletion, Datetime, Subqueries, Files, Operations, Query, Introspection, Window, Composite, State, Compiler, Query Utils, Proxy, Signals, Serializer, Schema, Expressions, Math, Json, Tuple Lookups, Aggregates, Questioner, Generated, Functions, Indexes, Manager

### Special (COMP-20)

**Files:**
- `projects/django/django/db/migrations/operations/special.py`
**Downstream dependents (must re-test):** Models, Autodetector, Operations, Query Utils, Serializer

### Optimizer (COMP-21)

**Files:**
- `projects/django/django/db/migrations/optimizer.py`
**Downstream dependents (must re-test):** Writer, Autodetector, Graph, State, Loader, Serializer, Migration, Models, Fields

### Questioner (COMP-22)

**Files:**
- `projects/django/django/db/migrations/questioner.py`
**Downstream dependents (must re-test):** Writer, Autodetector, Loader, Graph, State, Serializer, Migration, Models, Fields

### Recorder (COMP-23)

**Files:**
- `projects/django/django/db/migrations/recorder.py`
**Downstream dependents (must re-test):** Graph, State, Executor, Serializer, Models, Migration, Fields, Writer, Autodetector, Loader

### Serializer (COMP-24)

**Files:**
- `projects/django/django/db/migrations/serializer.py`
**Downstream dependents (must re-test):** Autodetector, Loader, Graph, State, Models, Migration, Fields, Writer

### State (COMP-25)

**Files:**
- `projects/django/django/db/migrations/state.py`
**Downstream dependents (must re-test):** Models, Autodetector, Fields, Writer, Loader, Executor, Serializer, Graph, Migration

### Writer (COMP-26)

**Files:**
- `projects/django/django/db/migrations/writer.py`
**Downstream dependents (must re-test):** Loader, Serializer, Graph, Migration, State, Models, Fields, Autodetector

### Aggregates (COMP-27)

**Files:**
- `projects/django/django/db/models/aggregates.py`
**Downstream dependents (must re-test):** Query, Window, State, Tuple Lookups, Functions, Signals, Manager, Models, Uuid, Comparison, Expressions, Constraints, Math, Json, Questioner, Generated, Indexes, Subqueries, Related Lookups, Mixins, Fields, Files, Options, Text, Related, Datastructures, Autodetector, Introspection, Where, Composite, Deletion, Compiler, Query Utils, Proxy, Datetime, Serializer, Schema, Operations

### Constraints (COMP-28)

**Files:**
- `projects/django/django/db/models/constraints.py`
**Downstream dependents (must re-test):** Introspection, Where, Composite, Deletion, Query Utils, Proxy, Datetime, Schema, Files, Operations, Query, Window, State, Tuple Lookups, Compiler, Aggregates, Signals, Serializer, Models, Expressions, Math, Json, Questioner, Generated, Functions, Indexes, Manager, Subqueries, Related Lookups, Mixins, Fields, Options, Uuid, Comparison, Text, Related, Datastructures, Autodetector

### Deletion (COMP-29)

**Files:**
- `projects/django/django/db/models/deletion.py`
**Downstream dependents (must re-test):** Window, Composite, State, Compiler, Query Utils, Proxy, Signals, Serializer, Schema, Models, Expressions, Math, Json, Tuple Lookups, Aggregates, Questioner, Generated, Functions, Indexes, Manager, Related Lookups, Mixins, Fields, Options, Uuid, Comparison, Text, Related, Constraints, Datastructures, Autodetector, Where, Datetime, Subqueries, Files, Operations, Query, Introspection

### Enums (COMP-30)

**Files:**
- `projects/django/django/db/models/enums.py`
**Downstream dependents (must re-test):** Proxy, Datetime, Schema, Files, Operations, Query, Window, State, Tuple Lookups, Compiler, Aggregates, Functions, Signals, Serializer, Models, Expressions, Constraints, Math, Json, Questioner, Generated, Indexes, Manager, Subqueries, Related Lookups, Mixins, Fields, Options, Uuid, Comparison, Text, Related, Datastructures, Autodetector, Introspection, Where, Composite, Deletion, Query Utils

### Expressions (COMP-31)

**Files:**
- `projects/django/django/db/models/expressions.py`
**Downstream dependents (must re-test):** Schema, Operations, Query, Window, State, Tuple Lookups, Aggregates, Functions, Indexes, Signals, Manager, Models, Fields, Uuid, Comparison, Text, Constraints, Autodetector, Math, Json, Questioner, Generated, Datetime, Subqueries, Related Lookups, Mixins, Files, Options, Related, Datastructures, Introspection, Where, Composite, Deletion, Compiler, Query Utils, Proxy, Serializer

### Fetch Modes (COMP-32)

**Files:**
- `projects/django/django/db/models/fetch_modes.py`
**Downstream dependents (must re-test):** Serializer, Schema, Expressions, Query, Window, State, Tuple Lookups, Aggregates, Functions, Indexes, Signals, Manager, Models, Fields, Options, Uuid, Comparison, Text, Constraints, Autodetector, Math, Json, Deletion, Questioner, Generated, Datetime, Subqueries, Related Lookups, Mixins, Files, Related, Datastructures, Operations, Introspection, Where, Composite, Compiler, Query Utils, Proxy

### Composite (COMP-33)

**Files:**
- `projects/django/django/db/models/fields/composite.py`
**Downstream dependents (must re-test):** Aggregates, Related Lookups, Mixins, Models, Options, Uuid, Text, Related, Constraints, Datetime, Files, Operations, Query, State, Compiler, Query Utils, Schema, Math, Json, Window

### Files (COMP-34)

**Files:**
- `projects/django/django/db/models/fields/files.py`
**Downstream dependents (must re-test):** Schema, Models, Math, Json, Aggregates, Related Lookups, Mixins, Options, Uuid, Text, Related, Constraints, Datetime, Operations, Query, Window, Composite, State, Compiler, Query Utils

### Generated (COMP-35)

**Files:**
- `projects/django/django/db/models/fields/generated.py`
**Downstream dependents (must re-test):** Datetime, Files, Related, Operations, Query, Composite, State, Compiler, Query Utils, Schema, Math, Json, Window, Aggregates, Related Lookups, Mixins, Models, Options, Uuid, Text, Constraints

### Json (COMP-36)

**Files:**
- `projects/django/django/db/models/fields/json.py`
- `projects/django/django/db/models/functions/json.py`
**Downstream dependents (must re-test):** Where, Composite, Datetime, Files, Operations, Query, Window, State, Compiler, Query Utils, Schema, Models, Math, Aggregates, Indexes, Related Lookups, Mixins, Options, Uuid, Text, Related, Constraints

### Mixins (COMP-37)

**Files:**
- `projects/django/django/db/models/fields/mixins.py`
- `projects/django/django/db/models/functions/mixins.py`
**Downstream dependents (must re-test):** Indexes, Models, Options, Uuid, Text, Constraints, Where, Datetime, Related Lookups, Files, Reverse Related, Related, Operations, Query, Composite, State, Compiler, Query Utils, Schema, Math, Json, Window, Aggregates

### Proxy (COMP-38)

**Files:**
- `projects/django/django/db/models/fields/proxy.py`
**Downstream dependents (must re-test):** Options, Related, Composite, Compiler, Query Utils, Schema, Operations, Query, Window, State, Aggregates, Models, Uuid, Text, Constraints, Math, Json, Datetime, Related Lookups, Mixins, Files

### Related (COMP-39)

**Files:**
- `projects/django/django/db/models/fields/related.py`
- `projects/django/django/db/models/fields/related_descriptors.py`
- `projects/django/django/db/models/fields/related_lookups.py`
**Downstream dependents (must re-test):** Schema, Math, Json, Window, Aggregates, Mixins, Models, Options, Uuid, Text, Constraints, Datetime, Related Lookups, Files, Operations, Query, Composite, State, Compiler, Query Utils

### Related Lookups (COMP-41)

**Files:**
- `projects/django/django/db/models/lookups.py`
**Downstream dependents (must re-test):** Mixins, Fields, Options, Uuid, Comparison, Text, Related, Constraints, Datastructures, Autodetector, Where, Deletion, Datetime, Subqueries, Files, Operations, Query, Introspection, Window, Composite, State, Compiler, Query Utils, Proxy, Signals, Serializer, Schema, Models, Expressions, Math, Json, Tuple Lookups, Aggregates, Questioner, Generated, Functions, Indexes, Manager

### Reverse Related (COMP-42)

**Files:**
- `projects/django/django/db/models/fields/reverse_related.py`
**Downstream dependents (must re-test):** Datetime, Related Lookups, Mixins, Files, Options, Text, Related, Composite, Compiler, Query Utils, Schema, Operations, Query, Window, State, Aggregates, Models, Uuid, Constraints, Math, Json

### Tuple Lookups (COMP-43)

**Files:**
- `projects/django/django/db/models/fields/tuple_lookups.py`
**Downstream dependents (must re-test):** Datetime, Files, Operations, Query, Window, Composite, State, Compiler, Query Utils, Schema, Models, Math, Json, Aggregates, Related Lookups, Mixins, Options, Uuid, Text, Related, Constraints

### Comparison (COMP-44)

**Files:**
- `projects/django/django/db/models/functions/comparison.py`
**Downstream dependents (must re-test):** Math, Json, Aggregates, Indexes, Mixins, Text, Constraints, Where, Related, Operations, Query, Compiler, Query Utils

### Datetime (COMP-45)

**Files:**
- `projects/django/django/db/models/functions/datetime.py`
**Downstream dependents (must re-test):** Where, Compiler, Query Utils, Serializer, Schema, Expressions, Operations, Query, Aggregates, Functions, Indexes, Text, Constraints, Math, Json, Questioner, Mixins, Files, Related

### Math (COMP-46)

**Files:**
- `projects/django/django/db/models/functions/math.py`
**Downstream dependents (must re-test):** Constraints, Json, Related Lookups, Related, Operations, Query, Where, Compiler, Query Utils, Serializer, Aggregates, Functions, Indexes, Mixins, Text

### Text (COMP-47)

**Files:**
- `projects/django/django/db/models/functions/text.py`
**Downstream dependents (must re-test):** Math, Json, Related, Operations, Query, Where, State, Compiler, Query Utils, Transaction, Aggregates, Indexes, Mixins, Options, Constraints

### Uuid (COMP-48)

**Files:**
- `projects/django/django/db/models/functions/uuid.py`
**Downstream dependents (must re-test):** Expressions, Math, Json, Aggregates, Functions, Indexes, Mixins, Text, Related, Constraints, Where, Operations, Query, Compiler, Query Utils, Serializer

### Window (COMP-49)

**Files:**
- `projects/django/django/db/models/functions/window.py`
**Downstream dependents (must re-test):** Operations, Query, Aggregates, Constraints, Math, Json, Indexes, Mixins, Text, Related, Where, Compiler, Query Utils

### Indexes (COMP-50)

**Files:**
- `projects/django/django/db/models/indexes.py`
**Downstream dependents (must re-test):** Comparison, Text, Constraints, Datastructures, Autodetector, Where, Deletion, Questioner, Datetime, Subqueries, Files, Related, Operations, Query, Introspection, Composite, State, Compiler, Query Utils, Proxy, Serializer, Schema, Expressions, Math, Json, Window, Tuple Lookups, Aggregates, Generated, Functions, Signals, Manager, Related Lookups, Mixins, Models, Fields, Options, Uuid

### Manager (COMP-52)

**Files:**
- `projects/django/django/db/models/manager.py`
**Downstream dependents (must re-test):** Where, Deletion, Datetime, Subqueries, Files, Operations, Query, Introspection, Window, Composite, State, Compiler, Query Utils, Proxy, Serializer, Schema, Models, Expressions, Math, Json, Tuple Lookups, Aggregates, Questioner, Generated, Functions, Indexes, Signals, Related Lookups, Mixins, Fields, Options, Uuid, Comparison, Text, Related, Constraints, Datastructures, Autodetector

### Options (COMP-53)

**Files:**
- `projects/django/django/db/models/options.py`
**Downstream dependents (must re-test):** Comparison, Text, Related, Datastructures, Autodetector, Introspection, Where, Composite, Deletion, Query Utils, Proxy, Datetime, Schema, Files, Operations, Query, Window, State, Tuple Lookups, Compiler, Aggregates, Functions, Signals, Serializer, Models, Expressions, Constraints, Math, Json, Questioner, Generated, Indexes, Manager, Subqueries, Related Lookups, Mixins, Fields, Uuid

### Query (COMP-54)

**Files:**
- `projects/django/django/db/models/query.py`
- `projects/django/django/db/models/query_utils.py`
- `projects/django/django/db/models/sql/query.py`
**Downstream dependents (must re-test):** Json, Creation, Questioner, Generated, Indexes, Subqueries, Related Lookups, Mixins, Fields, Options, Text, Related, Datastructures, Autodetector, Introspection, Where, Composite, Deletion, Query Utils, Proxy, Datetime, Schema, Files, Operations, Features, Window, State, Tuple Lookups, Compiler, Aggregates, Functions, Signals, Serializer, Manager, Models, Uuid, Comparison, Expressions, Constraints, Math

### Query Utils (COMP-55)

**Files:**
- `projects/django/django/db/backends/base/base.py`
- `projects/django/django/db/backends/dummy/base.py`
- `projects/django/django/db/backends/mysql/base.py`
- `projects/django/django/db/backends/oracle/base.py`
- `projects/django/django/db/backends/oracle/utils.py`
- `projects/django/django/db/backends/postgresql/base.py`
- `projects/django/django/db/backends/sqlite3/base.py`
- `projects/django/django/db/backends/utils.py`
- `projects/django/django/db/migrations/operations/base.py`
- `projects/django/django/db/migrations/utils.py`
- `projects/django/django/db/models/base.py`
- `projects/django/django/db/models/utils.py`
- `projects/django/django/db/utils.py`
**Downstream dependents (must re-test):** Subqueries, Related Lookups, Mixins, Files, Reverse Related, Graph, Related, Datastructures, Operations, Introspection, Features, Where, Composite, Loader, Compiler, Client, Proxy, Executor, Serializer, Schema, Special, Expressions, Migration, Query, Window, Creation, State, Tuple Lookups, Transaction, Aggregates, Functions, Indexes, Signals, Manager, Models, Fields, Options, Uuid, Comparison, Text, Writer, Constraints, Autodetector, Math, Json, Deletion, Questioner, Enums, Generated, Recorder, Exceptions, Datetime, Validation

### Signals (COMP-56)

**Files:**
- `projects/django/django/db/backends/signals.py`
- `projects/django/django/db/models/signals.py`
**Downstream dependents (must re-test):** Aggregates, Questioner, Generated, Functions, Indexes, Manager, Related Lookups, Mixins, Fields, Options, Uuid, Comparison, Text, Related, Constraints, Datastructures, Autodetector, Where, Deletion, Datetime, Validation, Subqueries, Files, Operations, Query, Introspection, Features, Window, Composite, State, Compiler, Client, Query Utils, Proxy, Serializer, Schema, Models, Expressions, Math, Json, Creation, Tuple Lookups

### Datastructures (COMP-57)

**Files:**
- `projects/django/django/db/models/sql/datastructures.py`
**Downstream dependents (must re-test):** Generated, Subqueries, Related Lookups, Graph, Operations, Introspection, Features, Compiler, Query Utils, Schema, Query, Creation, Tuple Lookups, Indexes, Options, Constraints

### Subqueries (COMP-58)

**Files:**
- `projects/django/django/db/models/sql/subqueries.py`
**Downstream dependents (must re-test):** Creation, Generated, Indexes, Datastructures, Introspection, Query Utils, Schema, Operations, Query, Features, Tuple Lookups, Compiler, Constraints

### Where (COMP-59)

**Files:**
- `projects/django/django/db/models/sql/where.py`
**Downstream dependents (must re-test):** Datastructures, Introspection, Features, Compiler, Query Utils, Schema, Operations, Query, Creation, Tuple Lookups, Indexes, Constraints, Generated, Subqueries

### Transaction (COMP-60)

**Files:**
- `projects/django/django/db/transaction.py`
**Downstream dependents (must re-test):** Operations, Query, Features, Window, State, Tuple Lookups, Compiler, Client, Aggregates, Executor, Functions, Signals, Serializer, Manager, Models, Uuid, Comparison, Expressions, Migration, Constraints, Math, Json, Creation, Questioner, Generated, Recorder, Exceptions, Indexes, Subqueries, Related Lookups, Mixins, Fields, Options, Text, Writer, Related, Datastructures, Autodetector, Introspection, Where, Composite, Deletion, Loader, Query Utils, Proxy, Datetime, Validation, Schema, Files, Special, Graph

### Infrastructure (COMP-62)

**Files:**
- `projects/django/django/db/backends/postgresql/psycopg_any.py`
- `projects/django/django/db/models/constants.py`
- `projects/django/django/db/models/sql/constants.py`
**Downstream dependents (must re-test):** Creation, Questioner, Generated, Indexes, Subqueries, Related Lookups, Mixins, Fields, Options, Text, Related, Datastructures, Autodetector, Introspection, Where, Composite, Deletion, Query Utils, Proxy, Datetime, Schema, Files, Operations, Query, Features, Window, State, Tuple Lookups, Compiler, Aggregates, Functions, Signals, Serializer, Manager, Models, Uuid, Comparison, Expressions, Constraints, Math, Json

## Known Constraints

*No constraint allocations defined.*
