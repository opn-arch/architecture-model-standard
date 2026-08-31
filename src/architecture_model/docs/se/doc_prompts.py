"""Prompt templates for LLM-authored SE documentation.

Each doc type has a system prompt (role/purpose) and a user prompt template
that receives model context + code context placeholders.
"""

from __future__ import annotations

# Map of doc module name -> (system_prompt, user_prompt_template)
# user_prompt_template uses {model_context} and {code_context} placeholders

DOC_PROMPTS: dict[str, tuple[str, str]] = {
    "conops": (
        "You are a systems engineer writing a Concept of Operations (ConOps) document. "
        "Write for a technical audience who needs to understand the system's purpose, "
        "operational context, stakeholders, and high-level usage scenarios. "
        "Ground everything in the provided architecture model — do not invent features.",
        """# Task: Write a Concept of Operations document

## Architecture Model Context
{model_context}

## Code Context
{code_context}

Write a complete ConOps document in markdown covering:
1. **System Overview** — What is this system, what problem does it solve, who uses it
2. **Stakeholders & Actors** — Who interacts with the system and their goals
3. **Operational Scenarios** — Key usage workflows described narratively
4. **System Capabilities** — What the system can do (grouped logically)
5. **Operational Constraints** — Limitations, assumptions, dependencies
6. **System Context** — How it fits with external systems/services

Be specific. Use the actual component names, capabilities, and actors from the model.
Write 500-1500 words of substantive content. Use tables where appropriate.""",
    ),
    "functional_analysis": (
        "You are a systems engineer writing a Functional Analysis document. "
        "Describe what the system does functionally — its capabilities, how they decompose "
        "into behaviors, and how those behaviors are realized by components. "
        "Ground everything in the provided architecture model.",
        """# Task: Write a Functional Analysis document

## Architecture Model Context
{model_context}

## Code Context
{code_context}

Write a complete Functional Analysis document in markdown covering:
1. **Capability Inventory** — Table of all capabilities with substantive descriptions of what each does and why it exists
2. **Functional Decomposition** — How capabilities break down into behaviors/functions
3. **Capability-Component Mapping** — Which components realize which capabilities (with explanation)
4. **Behavioral Flows** — For the most important capabilities, describe the step-by-step flow of how they execute
5. **Functional Dependencies** — Which capabilities depend on others
6. **Gaps & Unrealized Capabilities** — Any capabilities without clear component realization

Use actual names from the model. Every capability should have a real description (not "—").
For behavioral flows, reference the actual function/class names from the code context.""",
    ),
    "logical_architecture": (
        "You are a systems engineer writing a Logical Architecture document. "
        "Describe the structural decomposition of the system — its components, layers, "
        "responsibilities, and how they interact. This is the core architecture description. "
        "Ground everything in the provided model and code.",
        """# Task: Write a Logical Architecture document

## Architecture Model Context
{model_context}

## Code Context
{code_context}

Write a complete Logical Architecture document in markdown covering:
1. **Architecture Overview** — High-level description of the system's structural organization
2. **Layer Structure** — What layers exist and their responsibilities (if applicable)
3. **Component Inventory** — Table with each component's name, purpose, responsibilities, and key files
4. **Component Interactions** — How components communicate (dependencies, data flow)
5. **Dependency Analysis** — Key dependency chains, potential coupling concerns
6. **Design Rationale** — Why the system is structured this way (infer from the organization)
7. **Mermaid Dependency Graph** — Include a mermaid graph showing component relationships

Every component MUST have a substantive description of its purpose and responsibilities.
Use the file lists and function signatures to ground component descriptions in reality.""",
    ),
    "requirements_analysis": (
        "You are a systems engineer writing a Requirements Analysis document. "
        "Document the functional and non-functional requirements of the system, "
        "derived from the architecture model and code patterns. "
        "Distinguish between what the system MUST do, SHOULD do, and COULD do.",
        """# Task: Write a Requirements Analysis document

## Architecture Model Context
{model_context}

## Code Context
{code_context}

Write a complete Requirements Analysis document in markdown covering:
1. **Functional Requirements** — What the system must do (derived from capabilities and behaviors)
2. **Non-Functional Requirements** — Performance, security, reliability, maintainability constraints (derived from code patterns, constraints in model)
3. **Interface Requirements** — What interfaces must the system expose/consume
4. **Data Requirements** — What data the system manages (derived from models/schemas)
5. **Requirement-Component Traceability** — Which components satisfy which requirements
6. **Priority Classification** — MoSCoW categorization based on how central each requirement is

Derive requirements from actual system behavior. Each requirement should be specific and testable.""",
    ),
    "use_cases": (
        "You are a systems engineer writing a Use Cases document. "
        "Document how actors interact with the system to achieve their goals. "
        "Each use case should have preconditions, a main flow, alternate flows, "
        "and postconditions. Ground in the model's actors and behaviors.",
        """# Task: Write a Use Cases document

## Architecture Model Context
{model_context}

## Code Context
{code_context}

Write a complete Use Cases document in markdown covering:
1. **Actor-Goal Matrix** — Table of actors and their primary goals
2. **Use Case Catalog** — For each significant behavior/workflow:
   - **Title** — Clear action-oriented name
   - **Actor** — Who initiates it
   - **Preconditions** — What must be true before
   - **Main Flow** — Step-by-step sequence (5-10 steps). For EACH step, identify:
     - Which component handles it (by ID and name)
     - What function/method is called
     - What data flows in/out
   - **Alternate Flows** — Error cases, edge cases
   - **Postconditions** — What's true after successful completion
3. **Component Involvement Matrix** — Table showing which components participate in which use cases
4. **Use Case Relationships** — Which use cases include/extend others

Write at least 5-8 detailed use cases covering the system's core workflows.
Reference actual API endpoints, CLI commands, or UI actions from the code context.
For each main flow step, explicitly name the component (e.g., "COMP-1 (Core) validates...").""",
    ),
    "interface_spec": (
        "You are a systems engineer writing an Interface Specification document. "
        "Document all interfaces the system exposes and consumes — APIs, CLIs, "
        "file formats, protocols, events. Be specific about data formats and contracts. "
        "Ground in the model's interfaces and code signatures.",
        """# Task: Write an Interface Specification document

## Architecture Model Context
{model_context}

## Code Context
{code_context}

Write a complete Interface Specification document in markdown covering:
1. **Interface Inventory** — Table of all interfaces with type, provider component, consumer(s)
2. **API Interfaces** — For each API/HTTP interface: endpoints, methods, request/response formats
3. **CLI Interfaces** — For each CLI: commands, arguments, options, output format
4. **Internal Interfaces** — Key module-to-module contracts (function signatures, protocols)
5. **Data Formats** — Key data structures/schemas exchanged between components
6. **Interface Dependencies** — Which interfaces depend on external systems

For each interface, specify: provider, consumer(s), protocol, data format, error handling.
Use actual function signatures and class definitions from the code context.""",
    ),
    "verification_validation": (
        "You are a systems engineer writing a Verification & Validation document. "
        "Document how the system's requirements are verified (tested) and how the "
        "system is validated against its intended purpose. Reference actual test files.",
        """# Task: Write a Verification & Validation document

## Architecture Model Context
{model_context}

## Code Context
{code_context}

Write a V&V document in markdown covering:
1. **V&V Strategy** — Overall approach to testing and validation
2. **Test Coverage Matrix** — Which components/capabilities have tests, which don't
3. **Test Types** — Unit tests, integration tests, E2E tests identified in the codebase
4. **Verification Methods** — How each requirement is verified (test, inspection, analysis, demo)
5. **Validation Approach** — How system fitness-for-purpose is confirmed
6. **Gaps** — Untested components or capabilities

Reference actual test files and test functions from the code context.""",
    ),
    "operations_manual": (
        "You are a systems engineer writing an Operations Manual. "
        "Document how to deploy, configure, monitor, and operate the system. "
        "Ground in actual code patterns (config files, env vars, scripts, etc.).",
        """# Task: Write an Operations Manual

## Architecture Model Context
{model_context}

## Code Context
{code_context}

Write an Operations Manual in markdown covering:
1. **Deployment** — How to deploy the system (infer from project structure, scripts, configs)
2. **Configuration** — Environment variables, config files, settings
3. **Monitoring & Health** — Health checks, logging, observability
4. **Common Operations** — Backup, restore, scaling, maintenance tasks
5. **Troubleshooting** — Common issues and their resolution
6. **Dependencies** — External services/systems required for operation

Be practical and specific. Reference actual file paths, commands, and config patterns.""",
    ),
    "maintenance_manual": (
        "You are a systems engineer writing a Maintenance Manual. "
        "Document how to maintain, extend, and evolve the codebase. "
        "This is for developers who need to modify the system.",
        """# Task: Write a Maintenance Manual

## Architecture Model Context
{model_context}

## Code Context
{code_context}

Write a Maintenance Manual in markdown covering:
1. **Development Setup** — How to set up the development environment
2. **Code Organization** — How the codebase is structured and why
3. **Extension Points** — Where and how to add new functionality
4. **Key Patterns** — Coding patterns used throughout (infer from code)
5. **Dependency Management** — How dependencies are managed
6. **Common Maintenance Tasks** — Adding components, modifying interfaces, updating schemas

Ground in actual project structure, build tools, and coding patterns observed.""",
    ),
    "risk_assessment": (
        "You are a systems engineer writing a Risk Assessment document. "
        "Identify technical risks, architectural weaknesses, and potential failure modes. "
        "Ground in the actual architecture — coupling, complexity, missing tests, etc.",
        """# Task: Write a Risk Assessment document

## Architecture Model Context
{model_context}

## Code Context
{code_context}

Write a Risk Assessment document in markdown covering:
1. **Risk Register** — Table with: Risk ID, Description, Likelihood, Impact, Mitigation
2. **Architectural Risks** — Tight coupling, single points of failure, scalability limits
3. **Technical Debt** — Areas of the codebase that are fragile or overly complex
4. **Dependency Risks** — External dependencies that could cause issues
5. **Security Risks** — Potential vulnerabilities (infer from patterns)
6. **Operational Risks** — What can go wrong in production

Be honest and specific. Reference actual components and their complexity metrics.""",
    ),
    # Project-specific docs
    "api_reference": (
        "You are a technical writer documenting a REST/HTTP API. "
        "Write clear, complete API documentation with all endpoints, methods, "
        "parameters, request/response bodies, and error codes.",
        """# Task: Write an API Reference document

## Architecture Model Context
{model_context}

## Code Context
{code_context}

Write a complete API Reference in markdown covering all HTTP endpoints:
- For each endpoint: method, path, description, parameters, request body, response body, error codes
- Group endpoints by resource/domain
- Include example request/response pairs where possible
- Note authentication requirements if apparent

Use actual route definitions and handler signatures from the code context.""",
    ),
    "cli_reference": (
        "You are a technical writer documenting a CLI tool. "
        "Write clear documentation for all commands with their arguments, options, and examples.",
        """# Task: Write a CLI Reference document

## Architecture Model Context
{model_context}

## Code Context
{code_context}

Write a complete CLI Reference in markdown covering all commands:
- For each command: name, description, arguments, options, examples
- Group commands by category/subcommand
- Include usage examples

Use actual CLI definitions from the code context.""",
    ),
    "data_model": (
        "You are a systems engineer documenting a data model. "
        "Write clear documentation of all data entities, their relationships, "
        "and the overall data architecture.",
        """# Task: Write a Data Model document

## Architecture Model Context
{model_context}

## Code Context
{code_context}

Write a Data Model document in markdown covering:
1. **Entity Inventory** — All data entities/tables/models with their fields
2. **Relationships** — How entities relate (foreign keys, associations)
3. **Data Flow** — How data moves through the system
4. **Schema Diagram** — Mermaid ER diagram if possible
5. **Data Lifecycle** — Creation, modification, deletion patterns

Use actual model/schema definitions from the code context.""",
    ),
    "deployment_guide": (
        "You are a DevOps engineer writing a deployment guide. "
        "Document the complete deployment process grounded in actual project config.",
        """# Task: Write a Deployment Guide

## Architecture Model Context
{model_context}

## Code Context
{code_context}

Write a Deployment Guide in markdown covering:
1. **Prerequisites** — Required tools, services, accounts
2. **Build Process** — How to build the project
3. **Deployment Steps** — Step-by-step deployment instructions
4. **Environment Configuration** — All environment variables and config
5. **Verification** — How to verify successful deployment
6. **Rollback** — How to roll back a bad deployment

Ground in actual build files, Docker configs, CI/CD patterns found in the project.""",
    ),
    "security_analysis": (
        "You are a security engineer writing a security analysis. "
        "Identify security boundaries, authentication/authorization patterns, "
        "and potential vulnerabilities grounded in the actual codebase.",
        """# Task: Write a Security Analysis document

## Architecture Model Context
{model_context}

## Code Context
{code_context}

Write a Security Analysis in markdown covering:
1. **Security Boundaries** — Trust zones in the architecture
2. **Authentication & Authorization** — How users/services are authenticated
3. **Data Protection** — Encryption, sensitive data handling
4. **Input Validation** — How inputs are validated/sanitized
5. **Vulnerability Assessment** — Potential security issues
6. **Security Controls** — Existing mitigations

Reference actual security-related code patterns (auth middleware, validators, etc.).""",
    ),
    "plugin_guide": (
        "You are a developer advocate writing a plugin/extension development guide. "
        "This is NOT a maintenance manual — it's specifically about how third parties "
        "can extend the system WITHOUT modifying core code. Focus on extension points, "
        "hooks, interfaces, and the plugin lifecycle.",
        """# Task: Write a Plugin Development Guide

## Architecture Model Context
{model_context}

## Code Context
{code_context}

Write a Plugin Guide in markdown covering:
1. **Extension Architecture** — How the system supports extensibility (plugin loading, hooks, registries)
2. **Extension Points** — Specific interfaces/hooks that plugins implement (list each with signature)
3. **Plugin Lifecycle** — Discovery, registration, initialization, execution, cleanup
4. **Step-by-Step Tutorial** — Create a minimal plugin from scratch (with code)
5. **Advanced Patterns** — Composing plugins, dependencies between plugins, versioning
6. **Testing Plugins** — How to test plugin code in isolation and integration
7. **Distribution** — How to package and distribute plugins

NOTE: This is different from the Maintenance Manual which covers modifying CORE code.
This guide is for EXTERNAL developers who want to extend the system through its public extension API.
Reference actual interfaces, base classes, and registration patterns from the code.""",
    ),
    "behavior_flows": (
        "You are a systems engineer writing a Behavior Flows document. "
        "Write for a technical audience who needs to understand how the system's behaviors "
        "execute step-by-step and which components are involved at each stage. "
        "Ground everything in the provided architecture model — do not invent behaviors.",
        """You are writing a **Behavior Flows** document for {project}.

## Model Context
{model_context}

## Code Context
{code_context}

Write a Behavior Flows document in markdown covering:
1. **Behavior Overview** — Table of all behaviors with type, steps, and linked components
2. **Trigger Graph** — Mermaid diagram showing which behaviors trigger others
3. **Detailed Flows** — For each behavior: description, steps with component mapping, actors involved
4. **Cross-Component Flows** — Behaviors that span multiple components, showing the handoff sequence
5. **Error Handling Flows** — How behaviors handle failures and edge cases

Reference actual behavior definitions, steps, and component connections from the model.""",
    ),
}


def get_prompt(doc_name: str) -> tuple[str, str] | None:
    """Get (system_prompt, user_prompt_template) for a doc type.

    Returns None if no prompt is defined for this doc type.
    """
    return DOC_PROMPTS.get(doc_name)
