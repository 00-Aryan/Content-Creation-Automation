# Architectural Decisions (ADR)

This document records the major architectural decisions and rationales.

## ADR 1: SQLite Retained for Single-Operator MVP
- **Status**: Accepted
- **Context**: The application is currently designed for single-operator use cases.
- **Decision**: SQLite will be retained as the primary datastore to avoid infrastructure overhead.
- **Consequences**: Easy local setup and zero-admin overhead. Requires transition if multi-tenant support is introduced.

## ADR 2: Event-Driven Architecture Adopted
- **Status**: Accepted
- **Context**: Decoupling components is necessary to ensure audit trails, metrics, and notification dispatch do not block core workflow execution.
- **Decision**: An event broker is used to publish events asynchronously/synchronously to registered subscribers.
- **Consequences**: High modularity and cleaner separation of concerns.

## ADR 3: WorkflowActionExecutor is Mandatory Action Gateway
- **Status**: Accepted
- **Context**: State changes and actions must be verified, checked for availability, and logged consistently.
- **Decision**: All workflow action executions must pass through the `WorkflowActionExecutor`. Direct modification of topic/asset state is prohibited.
- **Consequences**: Guaranteed enforcement of transition rules and availability guards.

## ADR 4: Metrics/Audit/Notifications Originate from Events
- **Status**: Accepted
- **Context**: Observability and telemetry should be clean side-effects.
- **Decision**: Event subscribers (listeners) handle metrics collection, audit logging, and notifications.
- **Consequences**: Business logic is decoupled from telemetry and reporting.

## ADR 5: Streamlit Remains Presentation Layer Only
- **Status**: Accepted
- **Context**: Architectural separation between UI and business/data layers.
- **Decision**: Streamlit views must not access repositories or run raw workflows directly. They must use the API or service layer.
- **Consequences**: Enables swapping the frontend/presentation layer in the future without rewritten backend logic.

## ADR 6: Agent Workflow Files Committed to Repository
- **Status**: Accepted
- **Context**: Agent execution must be deterministic, repeatable, and version-controlled.
- **Decision**: All agent instructions, governance documents, and skill sets (e.g., `.agents/skills/`) are checked into git.
- **Consequences**: Collaborative and auditable agent-assisted development.
