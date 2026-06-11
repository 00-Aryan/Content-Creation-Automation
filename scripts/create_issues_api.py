#!/usr/bin/env python3
"""
Create GitHub Issues via REST API
This script creates all identified issues in the Content-Creation-Automation repository.
"""

import requests
import json
import os

# Configuration
OWNER = "00-Aryan"
REPO = "Content-Creation-Automation"
TOKEN = os.getenv("GITHUB_TOKEN")  # Set this environment variable with your GitHub token
API_URL = f"https://api.github.com/repos/{OWNER}/{REPO}/issues"

issues_data = [
    {
        "title": "[CODE QUALITY] Inconsistent Error Handling and Broad Exception Catches",
        "body": """## Description
Across various service files, particularly in `brief_generation_service.py` and `inference/providers/gemini.py`, there are instances of broad `except Exception as e:` clauses. While `inference/providers/gemini.py` attempts to classify `ClientError` and generic exceptions into `ProviderError`, the `brief_generation_service.py` still uses generic exception handling that might obscure specific issues and make debugging difficult. Additionally, `worker_daemon.py` contains `except Exception: pass` blocks around event publication, which can lead to silent failures in critical eventing.

## Problem
- Broad exception handling can mask underlying issues, making it hard to diagnose and fix problems
- Silent failures in event publication can lead to data inconsistencies or missed notifications
- Lack of specific error types or custom exceptions for domain-specific errors reduces traceability and maintainability

## Affected Files
- `src/content_creation/inference/providers/gemini.py`
- `src/content_creation/application/brief_generation_service.py` (lines 71-72, 95-102, 104-105)
- `src/content_creation/jobs/worker_daemon.py`

## Suggested Solutions
- Replace broad `except Exception` with more specific exception types where possible
- Implement custom exception classes for domain-specific errors (e.g., `BriefGenerationError`, `TopicProcessingError`)
- Ensure all caught exceptions are properly logged with sufficient context (e.g., stack traces, relevant data)
- Remove `except Exception: pass` blocks and handle or log all exceptions explicitly
- Consider using a centralized error handling mechanism or decorator for common error patterns""",
        "labels": ["bug", "refactor", "error-handling"]
    },
    {
        "title": "[CODE QUALITY] Outdated Python Type Hinting and Pydantic Usage",
        "body": """## Description
The project uses Python 3.10+ and Pydantic v2, but some patterns might not fully leverage the latest features for type safety and data validation. For example, the `published_at` field in `TopicItem` is stored as a `str` and then validated as ISO-8601. Pydantic v2 offers native `datetime` types that can handle this more robustly.

## Problem
- Not fully utilizing Pydantic v2's advanced features for data validation and serialization
- Manual string-based date validation can be error-prone and less efficient than native datetime types
- Potential for runtime type errors if data doesn't strictly conform to implicit expectations

## Affected Files
- `src/content_creation/models/topic.py` (lines 39-41, 54-64)
- `pyproject.toml`

## Suggested Solutions
- Update Pydantic models to use native Python types like `datetime` for date/time fields, leveraging Pydantic's automatic parsing and validation
- Explore Pydantic's `ConfigDict` for model configuration, `model_validator` for cross-field validation, and `computed_field` for derived attributes
- Ensure consistent use of type hints across the codebase, especially for function signatures and class attributes
- Review and update `pyproject.toml` to reflect the latest stable versions of dependencies, ensuring compatibility and access to new features""",
        "labels": ["enhancement", "refactor", "python", "pydantic"]
    },
    {
        "title": "[ARCHITECTURE] Repetitive Orchestration Logic and Tight Coupling in PipelineRunService",
        "body": """## Description
The `pipeline_run_service.py` exhibits a highly sequential and somewhat repetitive structure for orchestrating pipeline stages. Each stage constructs a new `WorkflowActionExecutor` inline and includes similar logic for execution, logging, and failure handling. This leads to tight coupling between the `PipelineRunService` and `WorkflowActionExecutor` and makes the pipeline less flexible for changes or parallel execution.

## Problem
- High coupling makes it difficult to modify or extend individual pipeline stages without affecting the entire service
- Repetitive code for stage execution and error handling increases maintenance burden and potential for inconsistencies
- The current fail-fast approach stops the entire pipeline on the first failure, which might not be desirable for all stages or scenarios
- Lack of a clear abstraction for pipeline stages hinders reusability and testability

## Affected Files
- `src/content_creation/application/pipeline_run_service.py`

## Suggested Solutions
- Introduce an abstract `PipelineStage` interface or base class to encapsulate common stage logic (e.g., execution, logging, status updates)
- Implement each pipeline step as a separate, configurable stage that adheres to this interface
- Use a more flexible orchestration engine that can manage stage dependencies, retries, and partial progress
- Consider a more declarative approach to define the pipeline flow, potentially using a directed acyclic graph (DAG) library if complexity warrants
- Decouple the `WorkflowActionExecutor` instantiation from the `PipelineRunService` by injecting it or using a factory pattern""",
        "labels": ["refactor", "architecture", "maintainability"]
    },
    {
        "title": "[JOBS] Direct Access to Private Attributes and Ad-Hoc Thread Management in WorkerDaemon",
        "body": """## Description
The `worker_daemon.py` directly accesses private attributes of the `queue_engine` (e.g., `queue_engine._repo`). Additionally, it manages per-job heartbeat threads and implements ad-hoc requeueing logic under lock contention. This approach can lead to fragile code, difficult-to-debug concurrency issues, and reduced maintainability.

## Problem
- Direct access to private attributes violates encapsulation and creates tight coupling
- Manual thread management for heartbeats increases complexity and potential for resource leaks or deadlocks
- Ad-hoc requeueing logic can be difficult to reason about and may not handle all edge cases correctly
- Swallowed event failures can lead to critical information loss

## Affected Files
- `src/content_creation/jobs/worker_daemon.py`
- `src/content_creation/jobs/sqlite_repository.py`

## Suggested Solutions
- Refactor `queue_engine` to expose necessary functionality through public methods, eliminating direct private attribute access
- Centralize thread management or use a more robust concurrency framework (e.g., `concurrent.futures`, `asyncio` if the project moves to async) for background tasks like heartbeats
- Improve the job claiming and requeueing mechanism to be more robust and less prone to race conditions, potentially leveraging database-level transactions more explicitly
- Ensure all event publication failures are logged and handled appropriately, rather than being silently suppressed""",
        "labels": ["bug", "refactor", "concurrency", "jobs"]
    }
]

def create_issue(title, body, labels):
    """Create a single GitHub issue"""
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    
    payload = {
        "title": title,
        "body": body,
        "labels": labels
    }
    
    response = requests.post(API_URL, headers=headers, json=payload)
    return response

if __name__ == "__main__":
    if not TOKEN:
        print("Error: GITHUB_TOKEN environment variable not set")
        print("Set it with: export GITHUB_TOKEN=<your-token>")
        exit(1)
    
    print(f"Creating {len(issues_data)} issues in {OWNER}/{REPO}")
    print("=" * 60)
    
    for i, issue in enumerate(issues_data, 1):
        print(f"\n[{i}/{len(issues_data)}] Creating: {issue['title']}")
        response = create_issue(issue['title'], issue['body'], issue['labels'])
        
        if response.status_code == 201:
            data = response.json()
            print(f"✓ Created successfully: {data['html_url']}")
        else:
            print(f"✗ Failed: {response.status_code}")
            print(f"  Response: {response.text}")
    
    print("\n" + "=" * 60)
    print("Issue creation complete!")
