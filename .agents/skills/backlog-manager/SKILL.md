---
name: backlog-manager
description: Create, update, classify, and prioritize backlog items with severity, phase target, status, and acceptance criteria.
---

# Skill: Backlog Manager

## Name
backlog-manager

## Description
Converts audit findings, architectural reviews, or code debt reports into structured, actionable backlog and tech debt items.

## Goal
Extract unresolved issues, assign correct severity, deduplicate with existing backlog entries, suggest the most appropriate implementation phase, and update the backlog and tech debt files.

## Procedure
1. **Source Parsing**:
   - Read the incoming audit reports, issue logs, or code review findings.
   - Scan `docs/project/BACKLOG.md` and `docs/project/TECH_DEBT.md` to prevent duplication.
2. **Evaluation**:
   - Classify issues based on severity (Critical, High, Medium, Low).
   - Trace the source phase where the issue originated.
   - Identify which future phase is recommended to resolve the issue.
3. **Tracking Update**:
   - Insert new structured entries into `docs/project/BACKLOG.md` using the standard tabular format (ID, Title, Severity, Source Phase, Status, Recommended Phase).
   - If an item is classified as technical debt (e.g. repeated code, poor test coverage, large file sizes), update `docs/project/TECH_DEBT.md`.
4. **Halt**: Report back the list of newly structured backlog items.

## Constraints
- **Structured Schema**: Follow the exact markdown table format and structure in the backlog tracking files.
- **No Direct App Edits**: Do not modify application code or behavior.

## Output Format
A summary of the backlog operations:
- **Analyzed Source**: The audits or logs examined.
- **Newly Added Items**: Structured table showing IDs and titles.
- **Deduplicated Items**: List of issues matched to existing backlog items.
- **Updated Tracking Files**: List of modified tracking documents.
