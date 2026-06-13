# Platform Quality Gates

This document defines the quality gates, automated checks, and manual review guidelines that all generated platform assets must pass before they are marked as ready for export or publishing.

---

## 1. Automated Pre-Publish Checks

The following checks are run programmatically before any asset is presented to the operator in the Streamlit UI:

| Gate | Check Type | Target | Limit/Condition | Action on Failure |
| :--- | :--- | :--- | :--- | :--- |
| **QG-01** | Deterministic | Character Count | LinkedIn: <= 1,800 chars (soft), <= 3,000 (hard) | Block transition to `READY` |
| **QG-02** | Deterministic | Word Count | YouTube Shorts: 130 to 150 words | Block transition to `READY` |
| **QG-03** | Deterministic | Grounding Reference | `grounding_map` must contain at least 1 entry per major section | Block transition to `READY` |
| **QG-04** | Pattern Match | Bad Emoji Count | Maximum of 3 emojis per post / script | Warning to operator |
| **QG-05** | Pattern Match | Hype Words | Zero matches for: "revolutionary", "game-changing", "mind-blowing" | Block transition to `READY` |

---

## 2. Validation Commands and Tests

To run these checks locally, use the following validation scripts:

```bash
# 1. Verify file structures and schemas (runs syntax checks)
uv run python -m pytest tests/ui/

# 2. Run deterministic content validator (stub script to be implemented in Phase 12.4)
# uv run python -m content_creation.validation.content_validator --post-path path/to/generated_post.json
```

---

## 3. Manual Review Guidelines

Even if all automated quality gates pass, a human operator must perform a manual review in the Brief Viewer / Editor UI before final export.

### 3.1 Review Checklist
1. **Fact Check**: Verify that numerical metrics match the paper exactly.
2. **Pacing Check** (YouTube Shorts): Read the spoken script column aloud with a stopwatch. Ensure it can be spoken comfortably in under 55 seconds.
3. **Layout Check** (LinkedIn): Preview the post in a mock LinkedIn feed container. Ensure the hook lines do not get cut off awkwardly by the "...see more" button.
4. **Link Verification**: Click on all links in the citation block. Ensure they resolve to the intended arXiv or repository pages.

---

## 4. State Transitions and Enforcements

The `WorkflowActionExecutor` handles status changes for generated platform assets. Assets begin in `DRAFT` state and cannot transition to `APPROVED` or `READY_TO_PUBLISH` if any high-severity quality gate (QG-01, QG-02, QG-03, QG-05) fails.
These state restrictions are enforced at the repository layer using check constraints in `sqlite_repository.py`.
