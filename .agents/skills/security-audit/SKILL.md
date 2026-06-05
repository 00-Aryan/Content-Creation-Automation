# Skill: Security Audit

## Name
security-audit

## Description
Performs standard security and credential safety scans across the codebase, configuration files, and git history to prevent secret leakage.

## Goal
Identify any hardcoded secrets, API keys, credentials, or insecure logging/telemetry practices. Classify risks without attempting automatic remediation.

## Procedure
1. **Source Scanning**: Search config files (`.env`, `pyproject.toml`, YAMLs) and code bases for patterns matching keys, tokens, or credentials (e.g., `sk-`, `AIzaSy`, `GEMINI_API_KEY=`, etc.).
2. **Log & Telemetry Check**: Verify that event handlers, logger configurations, audit stores, and metrics repositories do not log or store parameter values containing sensitive data.
3. **Database Verification**: Ensure SQLite database files (`.db`) are ignored in git and contain no plain-text secrets or passwords.
4. **Risk Classification**: Classify identified items (e.g., Critical: active credential in codebase; Medium: credential key name in code but value loaded via env; Low: mock token in tests).
5. **No Remediation**: Compile findings. Do NOT modify files or attempt to rewrite git history unless explicitly authorized.

## Constraints
- **Zero Modification**: This is a read-only audit. Never attempt to "fix" or delete a secret automatically, as it could break environments or lose data.
- **Reporting Discretion**: Report vulnerabilities directly and securely.

## Output Format
A security report with:
- **Audit Scope**: Directory and files scanned.
- **Findings Table**: List of vulnerabilities showing file path, line number, category, description, and severity (Critical, High, Medium, Low).
- **Insecure Logging Check**: Statement verifying event payloads and logging structures are safe.
- **Recommended Action**: Proposed remediation steps for the user's manual approval.
