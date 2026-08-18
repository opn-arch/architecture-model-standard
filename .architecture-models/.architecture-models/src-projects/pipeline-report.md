# Pipeline Report: Src (projects)

**Generated:** 2026-08-18T12:31:40Z
**Total Duration:** 5049ms
**Stages:** 7

## LLM Summary

No LLM calls — deterministic pipeline run

## Stage Scores

| Stage | Score | Duration | LLM Calls |
|-------|-------|----------|-----------|
| observe | 100 | 4547ms | 0 |
| infer | 95 | 10ms | 0 |
| allocate | 51 | 20ms | 0 |
| contract | 0 | 0ms | 0 |
| relate | 100 | 472ms | 0 |
| specify | 50 | 0ms | 0 |
| validate | 0 | 0ms | 0 |

## Stage: observe
**Score:** 100 | **Duration:** 4547ms

### Deterministic Findings
- Discovered 229 modules
- 190 functions, 562 classes
- 806 import edges

### LLM Calls
*(none)*

### Diagnostics
*(none)*

### Uncertainties
- dynamic_import: Dynamic import in projects/textual/src/textual/_import_app.py:111
- dynamic_import: Dynamic import in projects/textual/src/textual/app.py:1578

## Stage: infer
**Score:** 95 | **Duration:** 10ms

### Deterministic Findings
- Inferred 197 capabilities
- 1 actors
- 26 behaviors

### LLM Calls
*(none)*

### Diagnostics
*(none)*

### Uncertainties
- complex_behavior: Compositor in projects/textual/src/textual/_compositor.py has 20 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: App in projects/textual/src/textual/app.py has 131 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: Color in projects/textual/src/textual/color.py has 25 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: Content in projects/textual/src/textual/content.py has 45 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: StylesBuilder in projects/textual/src/textual/css/_styles_builder.py has 57 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: DOMQuery in projects/textual/src/textual/css/query.py has 19 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: StylesBase in projects/textual/src/textual/css/styles.py has 27 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: RenderStyles in projects/textual/src/textual/css/styles.py has 17 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: Stylesheet in projects/textual/src/textual/css/stylesheet.py has 16 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: DocumentNavigator in projects/textual/src/textual/document/_document_navigator.py has 18 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: DOMNode in projects/textual/src/textual/dom.py has 67 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: Driver in projects/textual/src/textual/driver.py has 17 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: MouseEvent in projects/textual/src/textual/events.py has 19 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: Region in projects/textual/src/textual/geometry.py has 40 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: MessagePump in projects/textual/src/textual/message_pump.py has 23 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: Screen in projects/textual/src/textual/screen.py has 40 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: Strip in projects/textual/src/textual/strip.py has 26 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: Style in projects/textual/src/textual/style.py has 15 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: Widget in projects/textual/src/textual/widget.py has 171 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: DataTable in projects/textual/src/textual/widgets/_data_table.py has 64 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: Input in projects/textual/src/textual/widgets/_input.py has 39 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: MaskedInput in projects/textual/src/textual/widgets/_masked_input.py has 15 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: OptionList in projects/textual/src/textual/widgets/_option_list.py has 35 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: Tabs in projects/textual/src/textual/widgets/_tabs.py has 15 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: TextArea in projects/textual/src/textual/widgets/_text_area.py has 81 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: TreeNode in projects/textual/src/textual/widgets/_tree.py has 28 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: Tree in projects/textual/src/textual/widgets/_tree.py has 38 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: Worker in projects/textual/src/textual/worker.py has 16 public methods — needs LLM analysis to identify key workflows and use cases
- ambiguous_module: projects/textual/src/textual/__main__.py has no clear capability affiliation
- ambiguous_module: projects/textual/src/textual/_color_constants.py has no clear capability affiliation
- ambiguous_module: projects/textual/src/textual/_compat.py has no clear capability affiliation
- ambiguous_module: projects/textual/src/textual/_easing.py has no clear capability affiliation
- ambiguous_module: projects/textual/src/textual/_keyboard_protocol.py has no clear capability affiliation
- ambiguous_module: projects/textual/src/textual/_time.py has no clear capability affiliation
- ambiguous_module: projects/textual/src/textual/_tree_sitter.py has no clear capability affiliation
- ambiguous_module: projects/textual/src/textual/widgets/_digits.py has no clear capability affiliation
- ambiguous_module: projects/textual/src/textual/widgets/_markdown_viewer.py has no clear capability affiliation
- ambiguous_module: projects/textual/src/textual/widgets/_sparkline.py has no clear capability affiliation
- ambiguous_module: projects/textual/src/textual/widgets/_tab_pane.py has no clear capability affiliation

## Stage: allocate
**Score:** 51 | **Duration:** 20ms

### Deterministic Findings
- 164 components
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
**Score:** 100 | **Duration:** 472ms

### Deterministic Findings
- 14512 depends-on relationships
- 164 contains relationships
- 163 realizes relationships

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
**Score:** 0 | **Duration:** 0ms

### Deterministic Findings
- Score: 0/100
- 35 issues

### LLM Calls
*(none)*

### Diagnostics
*(none)*

### Uncertainties
- generic_capability_name: Capability 'Web Routes' (CAP-1) has a generic name. LLM analysis could produce a more specific business-oriented name.
