# TASK-036: Phase 12.2 validation sweep and knowledge base bootstrap

**Phase:** 12.2  
**Status:** DONE  
**Priority:** HIGH  
**Created:** 2026-06-12  
**Completed:** 2026-06-12  
**Requires approval:** YES  

## Objective

Close Phase 12.2 with an end-to-end validation sweep and create/update the project knowledge base so Phase 12.3 starts from a controlled SDLC baseline.

## Scope

### Files to modify

- `docs/project/CURRENT_STATE.md` — update current project status, latest commit, test baseline, completed Phase 12.2 tasks, and remaining risks.
- `docs/project/ROADMAP.md` — update roadmap from Phase 12.3 through portfolio readiness.
- `docs/project/PHASES.md` — mark Phase 12.2 as validation/closure complete and queue Phase 12.3.
- `docs/project/NEXT_ACTION.md` — set the next action to Phase 12.3 platform-aware content planning.
- `docs/project/BACKLOG.md` — add or update remaining backlog items: taxonomy warnings, layout stretching, Streamlit deprecations, platform-aware generation, LLM guardrails, LinkedIn export, Shorts flow, observability, portfolio readiness.

### Files to create

- `docs/phase-12.2-validation-sweep.md` — record validation evidence for all Phase 12.2 fixes.
- `docs/project/SDLC_STANDARD.md` — define project SDLC gates from requirements to release.
- `docs/project/CODING_STANDARDS.md` — define coding standards, architecture boundaries, testing expectations, and error-handling rules.
- `docs/project/QUALITY_GATES.md` — define required validation commands and pass/fail rules.
- `docs/project/SECURITY_BASELINE.md` — define secure development baseline inspired by NIST SSDF and OWASP ASVS.
- `docs/project/DECISION_LOG.md` — capture major product/architecture decisions made so far.
- `docs/project/SPRINT_PLAN.md` — define sprint plan from Phase 12.3 onward.

### Files to NOT touch

All source code, test files, prompts, configs, dependency files, scripts, and generated data files.

## Constraints

- This is a docs and validation task only.
- Do not modify Python source files.
- Do not modify tests.
- Do not modify prompts.
- Do not modify generated artifacts under `data/`.
- Do not modify dependency files:
  - `pyproject.toml`
  - `uv.lock`
- Do not modify protected automation files:
  - `run-tasks.sh`
  - `AGENTS.md`
  - `CLAUDE.md`
  - `.gitignore`
- Do not invent validation results. Run commands and record the actual outputs.
- If a command fails, document the failure honestly in `docs/phase-12.2-validation-sweep.md`.
- Current expected full-suite baseline is at least `1000 passed`.
- The validation sweep must verify the actual fixes from TASK-030 through TASK-035.
- Keep the knowledge base practical and execution-oriented. Avoid generic process filler.

## Implementation Steps

1. Run full test validation:

   ```bash
   export UV_CACHE_DIR=/tmp/uv-cache
   uv run python -m pytest --tb=short -q 2>&1 | tail -3
   ```

   Expected result:

   ```text
   1000 passed
   ```

   Exact count may be higher, but must not be lower.

2. Validate scoring differentiation from TASK-030:

   ```bash
   python3 - <<'PY'
   import json
   import pathlib

   score_files = list(pathlib.Path("data/scored").glob("*.json"))[:20]
   scores = []

   for f in score_files:
       try:
           d = json.loads(f.read_text())
           scores.append(d.get("quality_score", d.get("score", d.get("priority_score", 0))))
       except Exception as e:
           scores.append(f"ERROR:{f.name}:{e}")

   print("Files checked:", len(score_files))
   print("Sample scores:", scores)
   print("Unique values:", sorted(set(scores), key=str))

   numeric_scores = [s for s in scores if isinstance(s, (int, float))]
   if len(numeric_scores) > 1 and len(set(numeric_scores)) <= 1:
       raise SystemExit("FAIL: scoring still appears collapsed")
   print("PASS: scoring is differentiated or no scored sample set exists")
   PY
   ```

3. Validate script marker cleanup from TASK-031:

   ```bash
   python3 - <<'PY'
   import json
   import pathlib
   import re

   marker_re = re.compile(r"\((F|K|C)\)")
   scripts = list(pathlib.Path("data/scripts").glob("*.json"))

   leaked = []
   for f in scripts:
       try:
           d = json.loads(f.read_text())
       except Exception as e:
           print("ERROR:", f, e)
           continue

       content = json.dumps(d, ensure_ascii=False)
       if marker_re.search(content):
           leaked.append(f)

   print("Script files checked:", len(scripts))
   print("Files with marker leaks:", len(leaked))

   if leaked:
       for f in leaked[:10]:
           print("-", f)
       raise SystemExit("FAIL: standalone script markers still leak")

   print("PASS: no standalone (F)(K)(C) markers found in saved script output")
   PY
   ```

4. Validate thumbnail placeholder cleanup from TASK-032:

   ```bash
   python3 - <<'PY'
   import json
   import pathlib

   thumbnail_dirs = [
       pathlib.Path("data/thumbnails"),
       pathlib.Path("data/thumbnail_prompts"),
   ]

   files = []
   for d in thumbnail_dirs:
       if d.exists():
           files.extend(d.glob("*.json"))

   polluted = []
   for f in files:
       try:
           data = json.loads(f.read_text())
       except Exception as e:
           print("ERROR:", f, e)
           continue

       text = json.dumps(data, ensure_ascii=False)
       if "needs_review" in text:
           polluted.append(f)

   print("Thumbnail files checked:", len(files))
   print("Files containing literal needs_review:", len(polluted))

   if polluted:
       print("NOTE: Historical generated files may need regeneration if they predate TASK-032.")
       for f in polluted[:10]:
           print("-", f)

   print("PASS: generator fallback cleanup should be verified by tests and diagnostics")
   PY
   ```

5. Validate UI helper coverage from TASK-033 to TASK-035:

   ```bash
   export UV_CACHE_DIR=/tmp/uv-cache
   uv run python -m pytest tests/test_ui_status_helper.py tests/test_ui_timestamp_helper.py --tb=short -q
   uv run python -m pytest tests/workflow/test_action_availability_engine.py tests/workflow/test_workflow_action_executor.py --tb=short -q
   ```

6. Confirm Phase 12.2 diagnostic files exist:

   ```bash
   ls -1 docs/phase-12.2-*.md
   ```

   Required files should include:

   ```text
   docs/phase-12.2-scoring-diagnostics.md
   docs/phase-12.2-script-token-cleanup.md
   docs/phase-12.2-thumbnail-placeholder-cleanup.md
   docs/phase-12.2-terminal-state-message-cleanup.md
   docs/phase-12.2-review-status-label-cleanup.md
   docs/phase-12.2-timestamp-display-cleanup.md
   ```

7. Create `docs/phase-12.2-validation-sweep.md`.

   It must include:

   ```markdown
   # Phase 12.2 Validation Sweep

   ## Summary

   Phase 12.2 focused on output quality, review UX correctness, and operator-facing cleanup.

   ## Validation Baseline

   - Latest commit:
   - Full test result:
   - Date:
   - Operator:

   ## Completed Tasks

   | Task | Purpose | Commit/Status |
   |---|---|---|
   | TASK-030 | Differentiated scoring | |
   | TASK-031 | Removed script marker tokens | |
   | TASK-032 | Removed thumbnail placeholder pollution | |
   | TASK-033 | Cleaned terminal-state messages | |
   | TASK-034 | Cleaned review enum labels | |
   | TASK-035 | Cleaned timestamp display | |

   ## Evidence

   ### Scoring Differentiation

   Paste actual command output.

   ### Script Marker Cleanup

   Paste actual command output.

   ### Thumbnail Placeholder Cleanup

   Paste actual command output.

   ### UI Status and Timestamp Helpers

   Paste actual command output.

   ### Workflow Terminal-State Handling

   Paste actual command output.

   ## Remaining Non-Blocking Issues

   - Format taxonomy warnings
   - Wide-monitor layout stretching
   - Streamlit deprecation warnings

   ## Closure Decision

   Phase 12.2 is ready to close if all critical validation checks pass and the full test suite remains at or above 1000 passed.
   ```

8. Create or update `docs/project/SDLC_STANDARD.md`.

   Required sections:

   ```markdown
   # SDLC Standard

   ## 1. Requirements

   - Every phase starts with a clear objective.
   - Every task has a narrow scope.
   - Every task defines files to modify and files to create.
   - No implementation begins without acceptance criteria.

   ## 2. Design

   - Respect architecture boundaries.
   - UI must not access repositories or services directly.
   - Workflow changes must preserve state protection.
   - Generation changes must preserve source grounding.

   ## 3. Implementation

   - Small, isolated tasks.
   - No opportunistic refactors.
   - No unrelated cleanup inside feature tasks.
   - Deterministic behavior where possible.

   ## 4. Verification

   - Run targeted tests.
   - Run full suite.
   - Document evidence.
   - Do not accept lower test baseline.

   ## 5. Release

   - Commit one task at a time.
   - Use clear commit messages.
   - Push only after validation.
   - Update project knowledge base.

   ## 6. Retrospective

   - Record bugs found.
   - Record architecture decisions.
   - Convert lessons into future guardrails.
   ```

9. Create or update `docs/project/CODING_STANDARDS.md`.

   Required sections:

   ```markdown
   # Coding Standards

   ## Architecture Boundaries

   - UI routes through existing client/application/workflow layers.
   - No direct repository/service access from UI pages.
   - Domain, workflow, application, and UI responsibilities must remain separate.

   ## Python Standards

   - Prefer typed functions for new code.
   - Keep functions small and testable.
   - Avoid broad `except Exception` unless the error is logged and surfaced safely.
   - Do not silently swallow errors.

   ## Testing Standards

   - Every bug fix gets a regression test where practical.
   - Test both success and failure paths.
   - Preserve or increase full-suite baseline.
   - Use targeted tests before full tests.

   ## Error Handling

   - Operator-facing messages must be readable.
   - Internal errors may be logged but not exposed raw in UI.
   - Fallbacks must be explicit and test-covered.

   ## Content Quality

   - Generated content must be source-grounded.
   - No structural marker leaks.
   - No placeholder pollution.
   - No generic platform-agnostic output after Phase 12.3.
   ```

10. Create or update `docs/project/QUALITY_GATES.md`.

    Required gates:

    ```markdown
    # Quality Gates

    ## Per-Task Gates

    - Task card exists.
    - Scope has `### Files to modify` and `### Files to create`.
    - Targeted tests pass.
    - Full test suite passes.
    - No unrelated files modified.

    ## Phase Closure Gates

    - All critical bugs fixed.
    - Validation sweep documented.
    - Knowledge base updated.
    - Next phase has task plan.
    - Full test suite remains green.

    ## Required Commands

    ```bash
    export UV_CACHE_DIR=/tmp/uv-cache
    uv run python -m pytest --tb=short -q 2>&1 | tail -3
    ```

    ## Current Baseline

    - Minimum expected full suite: 1000 passed
    ```
    ```

11. Create or update `docs/project/SECURITY_BASELINE.md`.

    Required sections:

    ```markdown
    # Security Baseline

    ## Secure SDLC Expectations

    - Security checks are part of normal development, not a final step.
    - Secrets must never be logged.
    - Prompt/output handling must not expose credentials.
    - External API calls must fail safely.

    ## Application Security Baseline

    - Validate external inputs.
    - Preserve workflow authorization/state gates.
    - Avoid direct UI-to-storage shortcuts.
    - Use least privilege for future OAuth integrations.

    ## AI-Specific Safety

    - Generated content must preserve source grounding.
    - LLM failures must be visible and recoverable.
    - Do not auto-publish without explicit operator approval.
    - Quality guardrails must precede publishing integrations.

    ## Future Security Tasks

    - LinkedIn OAuth threat model
    - Secret rotation playbook
    - Provider failure handling
    - Audit log hardening
    ```

12. Create or update `docs/project/ROADMAP.md`.

    Required roadmap:

    ```markdown
    # Roadmap

    ## Phase 12.3 — Platform-Aware Content

    - TASK-040: Define platform content contracts
    - TASK-041: Add LinkedIn post generator
    - TASK-042: Add YouTube Shorts script generator
    - TASK-043: Add platform preview UI
    - TASK-044: Add platform-aware approval workflow

    ## Phase 12.4 — LLM Quality Guardrails

    - TASK-045: Define quality rubric
    - TASK-046: Add deterministic pre-flight content checks
    - TASK-047: Add LLM-as-judge evaluation
    - TASK-048: Add hallucination/source-grounding check
    - TASK-049: Add quality gate UI

    ## Phase 12.5 — LinkedIn Publishing

    - TASK-050: LinkedIn OAuth feasibility audit
    - TASK-051: LinkedIn draft exporter
    - TASK-052: LinkedIn OAuth integration
    - TASK-053: LinkedIn manual publish action

    ## Phase 12.6 — YouTube Shorts Flow

    - TASK-054: Shorts packaging schema
    - TASK-055: Shorts export UI
    - TASK-056: Voiceover-readability validation

    ## Phase 12.7 — Observability and Reliability

    - TASK-057: Pipeline health dashboard v2
    - TASK-058: Structured error taxonomy
    - TASK-059: Run history and audit log

    ## Phase 12.8 — Portfolio Readiness

    - TASK-060: Architecture documentation refresh
    - TASK-061: Demo dataset and reproducible demo flow
    - TASK-062: Public README upgrade
    - TASK-063: Portfolio case study
    ```

13. Create or update `docs/project/SPRINT_PLAN.md`.

    Required content:

    ```markdown
    # Sprint Plan

    ## Sprint 1 — Platform Contracts and Generators

    Goal: Phase 12.3 functional.

    - TASK-040: Define platform content contracts
    - TASK-041: Add LinkedIn post generator
    - TASK-042: Add YouTube Shorts generator
    - TASK-043: Platform preview UI

    Exit criteria:

    - LinkedIn and Shorts outputs are visibly different.
    - Outputs are source-grounded.
    - Tests remain green.
    - UI respects architecture boundaries.

    ## Sprint 2 — Platform Workflow and Quality Checks

    - TASK-044: Platform-specific approval
    - TASK-045: Quality rubric
    - TASK-046: Deterministic checks
    - TASK-047: LLM-as-judge
    - TASK-049: Quality UI

    ## Sprint 3 — LinkedIn Export/Publish Path

    - TASK-050: LinkedIn feasibility audit
    - TASK-051: LinkedIn draft exporter
    - TASK-052: OAuth integration if feasible
    - TASK-053: Manual publish action

    ## Sprint 4 — Shorts Packaging and Portfolio Readiness

    - TASK-054: Shorts packaging schema
    - TASK-055: Shorts export UI
    - TASK-056: Voiceover-readability checks
    - TASK-060: Architecture docs
    - TASK-061: Demo mode
    - TASK-062: README upgrade
    - TASK-063: Case study
    ```

14. Create or update `docs/project/DECISION_LOG.md`.

    Required entries:

    ```markdown
    # Decision Log

    ## Phase 12.2

    - Prioritized scoring before UI polish because all topic scores were collapsed.
    - Cleaned output pollution before platform-aware generation.
    - Preserved workflow state protection while improving operator messages.
    - Kept timestamp/status cleanup as UI display-layer changes.

    ## Phase 12.3 Direction

    - Build LinkedIn and YouTube Shorts first.
    - Keep manual review before publishing.
    - Add quality guardrails before auto-capable publishing.
    - Defer Instagram and Twitter/X.
    - Do not pursue SaaS/multi-user until personal workflow is reliable.
    ```

15. Update `docs/project/CURRENT_STATE.md`.

    Must include:

    ```markdown
    # Current State

    ## Project

    Content Creation Automation Platform

    ## Current Phase

    Phase 12.2 closure complete. Phase 12.3 ready to start.

    ## Latest Baseline

    - Full test suite:
    - Latest commit:
    - Date:

    ## Recently Completed

    - TASK-030 through TASK-035

    ## Next Action

    Start Phase 12.3 with TASK-040: Define platform content contracts.

    ## Open Risks

    - Platform-aware generation not implemented yet.
    - LLM quality guardrails not implemented yet.
    - LinkedIn publishing feasibility not validated yet.
    - Remaining UI polish: taxonomy warnings, layout stretching, Streamlit deprecations.
    ```

16. Update `docs/project/NEXT_ACTION.md`.

    Required content:

    ```markdown
    # Next Action

    Start Phase 12.3 — Platform-Aware Content.

    ## Immediate Next Task

    TASK-040: Define platform content contracts.

    ## Why

    Phase 12.2 fixed output-quality blockers. The next product bottleneck is that generated content is still not platform-aware.

    ## Guardrails

    - No platform publishing before quality guardrails.
    - No auto-posting without explicit operator approval.
    - UI must not bypass application/workflow layers.
    - All platform output must be source-grounded.
    ```

17. Update `docs/project/PHASES.md`.

    Required content:

    - Mark Phase 12.2 as complete.
    - Add Phase 12.3 as next.
    - Preserve useful existing historical phase information.
    - Do not delete previous phase history.

18. Update `docs/project/BACKLOG.md`.

    Required backlog items:

    ```markdown
    # Backlog

    ## Remaining Phase 12.2 Non-Blocking Polish

    - Fix format taxonomy warnings.
    - Fix wide-monitor layout stretching.
    - Clean Streamlit deprecation warnings.

    ## Phase 12.3

    - Platform contracts.
    - LinkedIn generator.
    - YouTube Shorts generator.
    - Platform preview UI.
    - Platform-aware approval workflow.

    ## Phase 12.4

    - Quality rubric.
    - Deterministic content checks.
    - LLM-as-judge.
    - Source-grounding checks.
    - Quality gate UI.

    ## Phase 12.5+

    - LinkedIn export/publish flow.
    - YouTube Shorts packaging.
    - Observability and reliability.
    - Portfolio readiness.
    ```

19. Final validation:

    ```bash
    export UV_CACHE_DIR=/tmp/uv-cache

    uv run python -m pytest --tb=short -q 2>&1 | tail -3

    test -f docs/phase-12.2-validation-sweep.md
    test -f docs/project/SDLC_STANDARD.md
    test -f docs/project/CODING_STANDARDS.md
    test -f docs/project/QUALITY_GATES.md
    test -f docs/project/SECURITY_BASELINE.md
    test -f docs/project/DECISION_LOG.md
    test -f docs/project/SPRINT_PLAN.md

    grep -RIn "Phase 12.3" docs/project docs/phase-12.2-validation-sweep.md
    ```

## Validation

```bash
export UV_CACHE_DIR=/tmp/uv-cache

uv run python -m pytest --tb=short -q 2>&1 | tail -3

test -f docs/phase-12.2-validation-sweep.md
test -f docs/project/SDLC_STANDARD.md
test -f docs/project/CODING_STANDARDS.md
test -f docs/project/QUALITY_GATES.md
test -f docs/project/SECURITY_BASELINE.md
test -f docs/project/DECISION_LOG.md
test -f docs/project/SPRINT_PLAN.md

grep -RIn "TASK-040" docs/project docs/phase-12.2-validation-sweep.md
```

## Success Criteria

- [ ] Full test suite shows at least `1000 passed`.
- [ ] Phase 12.2 validation sweep is documented.
- [ ] Scoring differentiation evidence is recorded.
- [ ] Script marker cleanup evidence is recorded.
- [ ] Thumbnail placeholder cleanup evidence is recorded.
- [ ] UI status/timestamp helper test evidence is recorded.
- [ ] Terminal-state workflow handling evidence is recorded.
- [ ] Project knowledge base is bootstrapped or updated.
- [ ] SDLC standard exists.
- [ ] Coding standards exist.
- [ ] Quality gates exist.
- [ ] Security baseline exists.
- [ ] Sprint plan exists.
- [ ] Decision log exists.
- [ ] Next action is Phase 12.3 / TASK-040.
- [ ] No source code, tests, prompts, configs, dependency files, scripts, or generated data files are modified.

## Depends On

TASK-035

## Commit Message

```text
docs(project): close phase 12.2 and bootstrap SDLC knowledge base (TASK-036)
```
