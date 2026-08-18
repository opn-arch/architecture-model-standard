# Pipeline Report: Projects (db)

**Generated:** 2026-08-18T12:32:17Z
**Total Duration:** 4561ms
**Stages:** 7

## LLM Summary

No LLM calls — deterministic pipeline run

## Stage Scores

| Stage | Score | Duration | LLM Calls |
|-------|-------|----------|-----------|
| observe | 100 | 4445ms | 0 |
| infer | 98 | 2ms | 0 |
| allocate | 58 | 17ms | 0 |
| contract | 0 | 0ms | 0 |
| relate | 100 | 97ms | 0 |
| specify | 50 | 0ms | 0 |
| validate | 80 | 0ms | 0 |

## Stage: observe
**Score:** 100 | **Duration:** 4445ms

### Deterministic Findings
- Discovered 109 modules
- 155 functions, 535 classes
- 280 import edges

### LLM Calls
*(none)*

### Diagnostics
*(none)*

### Uncertainties
- dynamic_import: Dynamic import in projects/django/django/db/migrations/questioner.py:45

## Stage: infer
**Score:** 98 | **Duration:** 2ms

### Deterministic Findings
- Inferred 61 capabilities
- 1 actors
- 19 behaviors

### LLM Calls
*(none)*

### Diagnostics
*(none)*

### Uncertainties
- complex_behavior: BaseDatabaseWrapper in projects/django/django/db/backends/base/base.py has 50 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: BaseDatabaseOperations in projects/django/django/db/backends/base/operations.py has 80 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: BaseDatabaseSchemaEditor in projects/django/django/db/backends/base/schema.py has 26 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: DatabaseWrapper in projects/django/django/db/backends/mysql/base.py has 17 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: DatabaseFeatures in projects/django/django/db/backends/mysql/features.py has 23 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: DatabaseOperations in projects/django/django/db/backends/mysql/operations.py has 31 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: DatabaseFeatures in projects/django/django/db/backends/oracle/features.py has 16 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: DatabaseOperations in projects/django/django/db/backends/oracle/operations.py has 47 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: DatabaseWrapper in projects/django/django/db/backends/postgresql/base.py has 15 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: DatabaseOperations in projects/django/django/db/backends/postgresql/operations.py has 34 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: DatabaseOperations in projects/django/django/db/backends/sqlite3/operations.py has 33 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: MigrationAutodetector in projects/django/django/db/migrations/autodetector.py has 33 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: ProjectState in projects/django/django/db/migrations/state.py has 28 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: Model in projects/django/django/db/models/base.py has 20 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: BaseExpression in projects/django/django/db/models/expressions.py has 28 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: RelatedField in projects/django/django/db/models/fields/related.py has 15 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: ForeignObject in projects/django/django/db/models/fields/related.py has 22 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: ForeignKey in projects/django/django/db/models/fields/related.py has 21 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: ManyToManyField in projects/django/django/db/models/fields/related.py has 16 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: ForeignObjectRel in projects/django/django/db/models/fields/reverse_related.py has 24 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: Lookup in projects/django/django/db/models/lookups.py has 17 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: Options in projects/django/django/db/models/options.py has 34 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: QuerySet in projects/django/django/db/models/query.py has 71 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: SQLCompiler in projects/django/django/db/models/sql/compiler.py has 28 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: Query in projects/django/django/db/models/sql/query.py has 83 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: WhereNode in projects/django/django/db/models/sql/where.py has 19 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: projects/django/django/db/backends/utils.py has 10 public functions with 3 cross-calls — likely contains workflow patterns
- complex_behavior: projects/django/django/db/transaction.py has 16 public functions with 24 cross-calls — likely contains workflow patterns
- ambiguous_module: projects/django/django/db/backends/postgresql/psycopg_any.py has no clear capability affiliation
- ambiguous_module: projects/django/django/db/backends/sqlite3/_functions.py has no clear capability affiliation

## Stage: allocate
**Score:** 58 | **Duration:** 17ms

### Deterministic Findings
- 58 components
- File coverage: 10000%
- 0 unallocated files

### LLM Calls
*(none)*

### Diagnostics
*(none)*

## Stage: contract
**Score:** 0 | **Duration:** 0ms

### Deterministic Findings
- 0 contracts

### LLM Calls
*(none)*

### Diagnostics
*(none)*

## Stage: relate
**Score:** 100 | **Duration:** 97ms

### Deterministic Findings
- 1255 depends-on relationships
- 58 contains relationships
- 57 realizes relationships

### LLM Calls
*(none)*

### Diagnostics
*(none)*

## Stage: specify
**Score:** 50 | **Duration:** 0ms

### Deterministic Findings
- 0 interfaces

### LLM Calls
*(none)*

### Diagnostics
*(none)*

## Stage: validate
**Score:** 80 | **Duration:** 0ms

### Deterministic Findings
- Score: 80/100
- 5 issues

### LLM Calls
*(none)*

### Diagnostics
*(none)*

### Uncertainties
- generic_capability_name: Capability 'Web Routes' (CAP-1) has a generic name. LLM analysis could produce a more specific business-oriented name.
