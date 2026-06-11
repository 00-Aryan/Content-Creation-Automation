# Consolidated GitHub Issues - Content Creation Automation

This document tracks all issues identified in the expert review of the Content-Creation-Automation repository.

## Code Quality & Maintainability Issues

### 1. Inconsistent Error Handling and Broad Exception Catches
- **Status**: Todo
- **Labels**: bug, refactor, error-handling
- **Priority**: High
- **Affected Files**: 
  - `src/content_creation/inference/providers/gemini.py`
  - `src/content_creation/application/brief_generation_service.py`
  - `src/content_creation/jobs/worker_daemon.py`

### 2. Outdated Python Type Hinting and Pydantic Usage
- **Status**: Todo
- **Labels**: enhancement, refactor, python, pydantic
- **Priority**: Medium
- **Affected Files**: 
  - `src/content_creation/models/topic.py`
  - `pyproject.toml`

### 3. Repetitive Orchestration Logic and Tight Coupling in PipelineRunService
- **Status**: Todo
- **Labels**: refactor, architecture, maintainability
- **Priority**: High
- **Affected Files**: 
  - `src/content_creation/application/pipeline_run_service.py`

### 4. Direct Access to Private Attributes and Ad-Hoc Thread Management in WorkerDaemon
- **Status**: Todo
- **Labels**: bug, refactor, concurrency, jobs
- **Priority**: High
- **Affected Files**: 
  - `src/content_creation/jobs/worker_daemon.py`
  - `src/content_creation/jobs/sqlite_repository.py`

## LLM/AI Prompting & Generation Issues

### 5. Suboptimal Gemini API Structured Output Usage
- **Status**: Todo
- **Labels**: enhancement, llm, gemini, prompt-engineering
- **Priority**: Medium
- **Affected Files**: 
  - `src/content_creation/generation/brief.py`

### 6. Hardcoded LLM Model and API Key Handling
- **Status**: Todo
- **Labels**: enhancement, configuration, llm
- **Priority**: Medium
- **Affected Files**: 
  - `src/content_creation/inference/providers/gemini.py`

## CI/CD Pipeline Issues

### 7. Duplicated and Inconsistent GitHub Actions Workflows
- **Status**: Todo
- **Labels**: ci/cd, refactor, maintenance
- **Priority**: High
- **Affected Files**: 
  - `.github/workflows/ci.yml`
  - `.github/workflows/tests.yml`
  - `.github/workflows/quality.yml`
  - `.github/workflows/coverage.yml`

### 8. CI Workflow Failure Due to Missing Pytest Installation
- **Status**: Todo
- **Labels**: bug, ci/cd, dependencies
- **Priority**: High
- **Affected Files**: 
  - `pyproject.toml`
  - `.github/workflows/tests.yml`

### 9. Code Quality Workflow Failing Due to Unformatted Files
- **Status**: Todo
- **Labels**: bug, ci/cd, code-quality
- **Priority**: High
- **Affected Files**: 
  - Multiple source files (173 files need formatting)
  - `.github/workflows/quality.yml`

### 10. Node.js 20 Deprecation Warning in GitHub Actions
- **Status**: Todo
- **Labels**: ci/cd, maintenance, dependencies
- **Priority**: Medium
- **Affected Files**: 
  - `.github/workflows/*.yml` (all workflow files)

## Streamlit UI & State Management Issues

### 11. Redundant init_session_state Calls and Potential Performance Overhead
- **Status**: Todo
- **Labels**: performance, streamlit, refactor
- **Priority**: Low
- **Affected Files**: 
  - `src/content_creation/ui/state/session.py`

## General Architectural & Scalability Improvements

### 12. Lack of Clear Abstraction for Pipeline Stages
- **Status**: Todo
- **Labels**: architecture, scalability, refactor
- **Priority**: Medium
- **Affected Files**: 
  - `src/content_creation/application/pipeline_run_service.py`

### 13. Inconsistent Python Versions in CI Workflows
- **Status**: Todo
- **Labels**: bug, ci/cd, dependencies
- **Priority**: Medium
- **Affected Files**: 
  - `.github/workflows/ci.yml`
  - `.github/workflows/tests.yml`
  - `pyproject.toml`

### 14. Potential for Deadlocks and Race Conditions in Job Locking
- **Status**: Todo
- **Labels**: bug, concurrency, jobs
- **Priority**: High
- **Affected Files**: 
  - `src/content_creation/jobs/worker_daemon.py`
  - `src/content_creation/jobs/sqlite_repository.py`
  - `src/content_creation/jobs/schema.py`

### 15. Overly Broad Exception Suppression in Credential Resolution
- **Status**: Todo
- **Labels**: bug, security, error-handling
- **Priority**: High
- **Affected Files**: 
  - `src/content_creation/inference/credentials.py`

### 16. Lack of Structured Logging for LLM Interactions
- **Status**: Todo
- **Labels**: enhancement, observability, llm
- **Priority**: Medium
- **Affected Files**: 
  - `src/content_creation/inference/providers/gemini.py`
  - `src/content_creation/inference/manager.py`

### 17. Missing Documentation for LLM Prompting Guidelines
- **Status**: Todo
- **Labels**: documentation, llm, prompt-engineering
- **Priority**: Medium
- **Affected Files**: 
  - `CLAUDE.md`
  - New file: `PROMPT_GUIDELINES.md`

### 18. Potential for Prompt Injection Vulnerabilities
- **Status**: Todo
- **Labels**: security, llm, prompt-engineering
- **Priority**: High
- **Affected Files**: 
  - `src/content_creation/generation/brief.py`

### 19. Scalability Concerns for Streamlit UI with Large User Base
- **Status**: Todo
- **Labels**: performance, scalability, streamlit
- **Priority**: Low
- **Affected Files**: 
  - `src/content_creation/ui/app.py` (and related UI files)

