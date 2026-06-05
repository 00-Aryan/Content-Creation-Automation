# Project Risks

This file tracks active operational, technical, and project risks.

- **SQLite Growth Over Time**: Database size and performance could degrade under high read/write loads as the platform grows.
- **Schema Evolution Without Migrations**: Evolving schemas without a migration framework risks data loss or synchronization drift across deployments.
- **Third-Party SDK Deprecation Warnings**: Upstream deprecation warnings (e.g., `google-genai` on Python 3.17+) may lead to future package incompatibilities.
- **SSE Behavior in Production Streamlit**: Server-Sent Events (SSE) streaming may exhibit unexpected buffering or connection-drop issues in production Streamlit configurations.
- **Single-Operator Assumptions**: The current system assumes a single operator. Moving to a multi-operator environment will require major refactoring.
- **Missing RBAC/Auth**: There is currently no Role-Based Access Control or user authentication, presenting a security/isolation risk if deployed to shared environments.
