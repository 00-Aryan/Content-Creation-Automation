# Phase 7 Validation Plan: v0.6 Backend Architecture

This document defines the validation strategy for the v0.6 backend architecture release. It is a planning artifact only: no validation tests, runtime scripts, or code changes are defined here as implementation work.

Target runtime pipeline:

```text
Collect
-> Score
-> Brief
-> Content Intelligence
-> Storyboard
-> Assets
-> Manifests
```

Current baseline: 241 automated tests passing after AssetGenerationService cleanup and PipelineRunService wiring.

---

## 1. Release Readiness Assessment

v0.6 is ready to enter validation. The major service boundaries are in place, storage and workflow stages exist for the new artifacts, asset generators consume storyboard-aware inputs, and the runtime pipeline now executes Content Intelligence and Storyboard before Assets.

Validation should not assume release readiness is complete. The remaining risks are integration and behavior risks that only become visible under end-to-end execution, resume execution, and controlled failure injection.

| Risk Area | Severity | Risk | Validation Focus |
|---|---:|---|---|
| Architecture | MEDIUM | PipelineRunService now invokes more LLM-backed stages, increasing orchestration surface and latency. | Verify stage order, exception-only failure semantics, and no stage bypass. |
| Integration | HIGH | Assets can still execute in storyboard fallback mode if storyboard artifacts are missing or skipped. | Prove assets consume storyboard-owned fields, not brief-only fields. |
| Workflow | MEDIUM | BriefGenerationService does not currently mark `brief` workflow completion, while downstream stages do mark their own states. | Verify expected state behavior and document any accepted asymmetry. |
| Storage | MEDIUM | CI and storyboard storage must persist across process restarts and be discoverable by downstream services. | Verify artifact files, reload behavior, and repository list/get paths. |
| State Management | HIGH | Existing file presence and workflow completion both influence skip behavior, and current services check completed workflow state before checking artifact existence. Divergence can mask missing artifacts. | Validate completed, failed, and missing-file combinations. |
| Artifact Consistency | HIGH | Topic identity must remain stable across staged, scored, brief, CI, storyboard, and all assets. | Verify topic IDs and source metadata across all artifacts. |
| Manifests | MEDIUM | ManifestBuilder may reflect asset readiness without directly validating CI/storyboard artifacts. | Verify manifest status matches generated assets and optional formats. |
| Runtime Observability | LOW | CLI may not print explicit CI/storyboard summaries even if PipelineLogger records them. | Verify structured logs contain all pipeline stages. |

Release readiness assessment: ready for validation execution, with storyboard ownership validation as the highest-priority release gate.

---

### Brief Workflow State Classification

Implementation source of truth:

- `src/content_creation/application/brief_generation_service.py`
- `src/content_creation/workflow/state.py`

Observed behavior:

- `WorkflowState` pre-initializes a `brief` stage.
- `BriefGenerationService.run()` writes brief artifacts through `ctx.storage.save_brief(brief)`.
- `BriefGenerationService.run()` skips existing brief files by checking `ctx.storage.briefs_dir / f"{item.id}.json"`.
- `BriefGenerationService.run()` does not call `ctx.workflow.mark_completed(..., "brief", ...)` and does not call `ctx.workflow.mark_failed(..., "brief", ...)`.

Classification:

- Intentional behavior: not determinable from code comments or service documentation.
- Temporary implementation gap: yes, from an architectural consistency standpoint. The workflow model includes `brief`, but the brief service does not update that state.
- Accepted v0.6 exception: yes for Phase 7 validation, because current runtime resumability for briefs is file-existence based and downstream services consume persisted brief artifacts rather than brief workflow state.
- Release readiness issue: not by itself, unless validation finds that the pending brief workflow state causes downstream execution, resume, manifest, or lineage failures.

Expected validation treatment:

- Do not fail v0.6 solely because `brief` remains `pending` while `data/briefs/{topic_id}.json` exists.
- Do record this asymmetry in the final validation evidence.
- Treat missing brief artifact as a failure regardless of workflow state.
- Treat downstream stages as authoritative only when both workflow behavior and artifact evidence match their expected contract.
- Raise a release issue if any code path requires `brief=completed` for correct execution, because current implementation does not provide that transition.

---

## 2. Validation Matrix

| Stage | Input Artifact | Output Artifact | Validation Criteria | Failure Conditions | Evidence Required |
|---|---|---|---|---|---|
| Collect | Feed config, source filter, raw remote/local source | Raw and staged topic files | New valid topics are staged; duplicates are skipped; source filter is honored. | Feed unavailable, malformed item, duplicate handling broken, staged file missing required fields. | Command output, staged JSON sample, raw/staged counts, pipeline log entry. |
| Score | Staged topic files | Scored topic files | Scored items contain status, priority score, scoring details, validation flags. | No scored output for valid staged input, rejected count incorrect, invalid status transition. | Scored JSON sample, score summary, rejection evidence. |
| Brief | Scored topics with `status=scored` | Brief JSON | Top-N selection respected; brief contains topic ID, summary, recommended formats, source URL. | Missing brief for eligible scored topic, malformed JSON, generation exception. | Brief JSON, generation summary, source URL continuity check. |
| Content Intelligence | Brief JSON plus scored/staged metadata | Content Intelligence JSON | CI exists per selected brief; topic metadata is resolved; workflow marks `content_intelligence` completed. | Missing CI for eligible brief, failed generator, missing scored/staged metadata fallback defect. | CI JSON, workflow state JSON, pipeline log stage summary. |
| Storyboard | Content Intelligence JSON plus matching Brief JSON | Storyboard JSON | Storyboard exists per CI item; storyboard fields contain visual metaphor, hooks, claims, CTAs; workflow marks `storyboard` completed. | Missing brief dependency, generator failure, malformed storyboard fields, skipped storyboard without prior artifact. | Storyboard JSON, workflow state JSON, service summary. |
| Assets | Brief JSON plus Storyboard JSON | Thumbnail, Script, Carousel, Newsletter JSON as applicable | Assets exist for required/recommended formats; storyboard-owned fields override LLM/brief values; workflow marks asset stages completed. | Asset missing, fallback to brief-only values, wrong format mapping, save failure. | Asset JSON samples, storyboard-to-asset field comparison, workflow state JSON. |
| Manifests | Brief and asset files | Topic manifest JSON | Manifest reflects required and optional assets; status is partial/complete/blocked according to asset review statuses. | Missing manifest, wrong skipped/generated asset status, stale manifest after asset changes. | Manifest JSON, asset status comparison, build summary. |

---

## 2A. Manifest Readiness Validation

Implementation source of truth:

- `src/content_creation/manifest.py`

Observed behavior:

- `ManifestBuilder.build_all()` builds manifests for topics with briefs.
- `ManifestBuilder.build()` checks only these asset classes: `brief`, `script`, `carousel`, `newsletter`, `thumbnail`.
- `content_intelligence` and `storyboard` are not manifest asset entries.
- Manifest `overall_status` and `ready_for_planner` are computed from non-skipped brief/asset statuses only.

Architectural answer:

- Current manifests certify **A) asset readiness only**.
- Current manifests do **not** certify successful completion of the entire content pipeline.
- CI and Storyboard existence must be validated separately through artifact lineage, workflow state, and pipeline logs.

### Scenario M1: Content Intelligence Missing, Storyboard Present, Assets Present

Procedure:

1. Create or preserve a brief artifact.
2. Remove `data/content_intelligence/{topic_id}.json`.
3. Preserve `data/storyboards/{topic_id}.json`.
4. Preserve generated asset files.
5. Build manifest.

Expected result:

- Manifest behavior is unchanged by missing Content Intelligence.
- Manifest status is based on brief and asset files only.
- If all non-skipped brief/assets are approved, manifest may report `complete` and `ready_for_planner=True` even though CI is missing.

Pass criteria:

- Manifest accurately reflects brief/asset statuses.
- Validation report separately flags missing CI as a pipeline lineage/workflow issue, not as a manifest computation defect.

Evidence required:

- Manifest JSON.
- Directory proof that CI is missing.
- Storyboard and asset artifact proof.
- Lineage validation note identifying CI gap outside manifest scope.

### Scenario M2: Storyboard Missing, Assets Present

Procedure:

1. Create or preserve a brief artifact.
2. Preserve asset files.
3. Remove `data/storyboards/{topic_id}.json`.
4. Build manifest.

Expected result:

- Manifest behavior is unchanged by missing Storyboard.
- Manifest status is based on brief and asset files only.
- If all non-skipped brief/assets are approved, manifest may report `complete` and `ready_for_planner=True` even though Storyboard is missing.

Pass criteria:

- Manifest accurately reflects brief/asset statuses.
- Validation report separately flags missing Storyboard as a pipeline lineage/workflow issue and a storyboard ownership validation blocker.

Evidence required:

- Manifest JSON.
- Directory proof that storyboard is missing.
- Asset artifact proof.
- Storyboard ownership validation failure note.

Release interpretation:

- A manifest that is correct according to `ManifestBuilder` can still coexist with an incomplete v0.6 pipeline lineage.
- Final release readiness must therefore require both manifest readiness evidence and separate CI/storyboard lineage evidence.

---

## 2B. Interface Contract Validation

Purpose: protect approved architecture contracts from regression. This is architecture validation, not behavioral validation.

Implementation sources of truth:

- `src/content_creation/generation/thumbnail.py`
- `src/content_creation/generation/carousel.py`
- `src/content_creation/generation/newsletter.py`
- `src/content_creation/generation/script.py`
- `src/content_creation/application/content_intelligence_service.py`
- `src/content_creation/application/storyboard_service.py`
- `src/content_creation/application/asset_generation_service.py`
- `src/content_creation/application/pipeline_run_service.py`
- `src/content_creation/storage/local.py`

Approved generator interfaces:

```python
ThumbnailGenerator.generate(storyboard, brief)
CarouselGenerator.generate(storyboard, brief)
NewsletterGenerator.generate(storyboard, brief)
ScriptGenerator.generate(storyboard, brief, format)
```

Validation criteria:

- Generator signatures remain storyboard-first.
- No generator reverts to `generate(brief)` or `generate(brief, storyboard=...)`.
- No compatibility shim is introduced to support both old and new call order.
- No dynamic argument remapping is introduced in services to hide mixed contracts.
- `AssetGenerationService` invokes generators using the approved contracts.
- `PipelineRunService` invokes services in fixed stage order rather than discovering or dynamically reordering services at runtime.

Approved service interfaces to validate:

- `ContentIntelligenceService.run(ctx, top_n=5, api_key=None, rate_limit_delay=5.0)`
- `StoryboardService.run(ctx, top_n=5, api_key=None, rate_limit_delay=5.0)`
- `AssetGenerationService.run(ctx, top_n=5, api_key=None, rate_limit_delay=5.0)`
- `PipelineRunService.run(ctx, top_n=5, source_filter=None, auto_approve=False, api_key=None)`

Approved storage interfaces to validate:

- `save_brief(brief)`
- `get_brief(topic_id)`
- `save_content_intelligence(ci)`
- `list_content_intelligence()`
- `save_storyboard(storyboard)`
- `get_storyboard(topic_id)`
- `save_thumbnail(thumbnail)`
- `save_script(script)`
- `save_carousel(carousel)`
- `save_newsletter(newsletter)`

Failure conditions:

- Any generator accepts or requires the old brief-first contract.
- Any service calls a generator with brief-first ordering.
- Any wrapper silently swaps argument order.
- Storage APIs are bypassed for CI, Storyboard, or generated assets in runtime orchestration.
- Pipeline stage wiring bypasses `ContentIntelligenceService` or `StoryboardService`.

Evidence required:

- Static signature inspection.
- Service invocation inspection.
- Targeted contract assertions in validation notes.
- Search evidence showing no stale brief-first production call sites.

---

## 3. End-to-End Validation Scenarios

### A. Happy Path: Single Topic Completes Entire Pipeline

Objective: prove one topic can traverse the complete v0.6 backend chain.

Procedure:

1. Start with isolated test storage.
2. Provide one valid source topic.
3. Run `run-pipeline --top 1`.
4. Verify generated artifacts for staged, scored, brief, content intelligence, storyboard, assets, and manifest.

Expected result:

- Pipeline stages execute in the configured order.
- One topic maintains the same topic ID through all artifacts.
- CI and storyboard files exist before assets are generated.
- Manifest exists and references generated assets.

Evidence:

- Pipeline log JSONL.
- One artifact JSON from every stage.
- Workflow state file for the topic.
- Manifest JSON.

### B. Multi-topic Batch

Objective: prove Top-N and batch processing work across multiple topics.

Procedure:

1. Seed at least three valid staged/scored candidates with distinct priority scores.
2. Run `run-pipeline --top 2`.
3. Verify only the two highest-priority eligible topics proceed through generation.

Expected result:

- Two briefs, two CI artifacts, two storyboards, and assets for the selected topics.
- Non-selected topic does not receive downstream generation artifacts.
- Counts in stage summaries match selected topics and recommended formats.

Evidence:

- Scored priority ordering.
- Artifact counts by directory.
- Pipeline summary counts.

### C. Empty Pipeline

Objective: prove empty inputs do not create invalid artifacts or crash the pipeline.

Procedure:

1. Use isolated storage with no feed results or no staged topics.
2. Run `run-pipeline --top 1`.
3. Verify graceful completion or controlled no-op behavior according to current service semantics.

Expected result:

- No invalid artifacts are created.
- Stage summaries are present.
- No unhandled exception occurs solely because there is no work.

Evidence:

- Pipeline log.
- Empty artifact directories.
- Console summary.

### D. Partial Resume

Objective: prove the pipeline resumes after interruption.

Procedure:

1. Generate artifacts through Brief or Content Intelligence.
2. Stop before Storyboard or Assets.
3. Re-run `run-pipeline --top 1`.
4. Verify completed/file-existing stages are skipped and missing downstream stages continue.

Expected result:

- Existing artifacts are not overwritten unless current service semantics intentionally allow it.
- Workflow completed stages remain completed.
- Missing downstream artifacts are generated.

Evidence:

- File timestamps or content hashes before and after resume.
- Workflow state before and after resume.
- Pipeline log showing skipped/generated counts.

### E. Failure Recovery: Content Intelligence Stage Failure

Objective: prove CI exceptions halt downstream pipeline execution and recovery works after rerun.

Procedure:

1. Inject a controlled exception in ContentIntelligenceService.
2. Run pipeline.
3. Verify Storyboard, Assets, and Manifests do not run.
4. Remove failure injection.
5. Re-run pipeline.

Expected result:

- PipelineRunService marks the CI stage failed only because an exception was raised.
- Downstream stages are not executed during failed run.
- On rerun, CI succeeds and downstream stages proceed.

Evidence:

- Pipeline result success false for failed run.
- Stage list ends at `generate-content-intelligence`.
- Workflow state for affected topic records `content_intelligence=failed` if service handles the topic-level failure before raising.
- Successful rerun artifacts.

### F. Failure Recovery: Storyboard Stage Failure

Objective: prove storyboard exceptions halt asset generation and recovery works.

Procedure:

1. Allow CI to succeed.
2. Inject a controlled exception in StoryboardService.
3. Run pipeline.
4. Verify Assets and Manifests do not run.
5. Remove failure injection and rerun.

Expected result:

- Storyboard stage failure stops AssetGenerationService invocation.
- No asset artifact is created from missing storyboard during exception-halting path.
- Rerun generates storyboard and assets.

Evidence:

- Pipeline stage list.
- Empty asset directories after failed run.
- Storyboard and asset artifacts after recovery.

### G. Failure Recovery: Asset Generation Failure

Objective: prove asset exceptions halt manifest generation and recovery works.

Procedure:

1. Allow CI and storyboard to succeed.
2. Inject a controlled exception in AssetGenerationService.
3. Run pipeline.
4. Verify manifests do not build.
5. Remove failure injection and rerun.

Expected result:

- Pipeline fails at `generate-assets`.
- Manifest stage does not execute during failed run.
- Rerun generates assets and manifests.

Evidence:

- Pipeline log stage status.
- Absence of new manifest after failed run.
- Manifest after recovery.

### H. Idempotency: Pipeline Executed Twice

Objective: prove a second run does not duplicate completed work.

Procedure:

1. Run pipeline to completion for one or more topics.
2. Capture artifact file list, content hashes, workflow states, and manifest count.
3. Run pipeline again with the same parameters.
4. Compare results.

Expected result:

- No duplicate files.
- Completed workflow stages remain completed.
- Existing artifacts are preserved.
- Stage summaries show skipped or zero generated where appropriate.

Evidence:

- Directory file counts before/after.
- Hash or timestamp comparison.
- Workflow state comparison.
- Pipeline log for second run.

### I. Storage Persistence

Objective: prove artifacts survive process restart and remain readable.

Procedure:

1. Run pipeline through Storyboard or Assets.
2. Terminate process.
3. Create a fresh ApplicationContext against the same base directory.
4. Read artifacts through storage APIs.
5. Continue pipeline or rebuild manifests.

Expected result:

- Storage list/get methods return persisted artifacts.
- Topic IDs and schema validations survive reload.
- Manifests can be rebuilt from persisted artifacts.

Evidence:

- Fresh-process storage read output.
- Artifact JSON.
- Manifest rebuild summary.

### J. Workflow / Artifact Divergence Recovery

Objective: validate behavior when workflow state and artifact storage disagree.

Implementation sources of truth:

- `src/content_creation/application/content_intelligence_service.py`
- `src/content_creation/application/storyboard_service.py`
- `src/content_creation/application/asset_generation_service.py`

Observed behavior:

- ContentIntelligenceService checks `ctx.workflow.stage_completed(topic_id, "content_intelligence")` before checking whether the CI file exists.
- StoryboardService checks `ctx.workflow.stage_completed(topic_id, "storyboard")` before checking whether the storyboard file exists.
- AssetGenerationService checks `ctx.workflow.stage_completed(topic_id, asset_type)` before checking whether the asset file exists.
- Therefore, if workflow says completed but the artifact is missing, current services skip regeneration.

Procedure:

1. Create valid upstream artifacts for the stage under test.
2. Create workflow state with the target stage marked `completed`.
3. Remove the corresponding target artifact file.
4. Re-run `run-pipeline`.
5. Capture workflow state, artifact directories, and pipeline logs.

Content Intelligence divergence:

- Setup: `content_intelligence=completed`, `data/content_intelligence/{topic_id}.json` missing.
- Expected behavior from current implementation: CI generation is skipped. Storyboard may not run for that topic because it lists CI artifacts from storage.
- Pass criteria: validation detects the divergence and records it as not self-healing.
- Evidence required: workflow state, missing CI file proof, pipeline log, absence of regenerated CI.

Storyboard divergence:

- Setup: `storyboard=completed`, `data/storyboards/{topic_id}.json` missing.
- Expected behavior from current implementation: Storyboard generation is skipped. AssetGenerationService loads `storyboard=None` and may generate assets in fallback mode if asset stages are pending.
- Pass criteria: validation detects the divergence and treats fallback asset generation as a release-blocking integrity failure unless explicitly waived.
- Evidence required: workflow state, missing storyboard file proof, asset output comparison, storyboard ownership validation result.

Asset divergence:

- Setup: one asset stage such as `thumbnail=completed`, but `data/thumbnails/{topic_id}.json` missing.
- Expected behavior from current implementation: that asset is skipped and not regenerated.
- Pass criteria: validation detects completed workflow state with missing artifact and records it as not self-healing.
- Evidence required: workflow state, missing asset file proof, pipeline log skipped/generated counts, manifest result showing missing asset if manifest builds.

Release interpretation:

- Current v0.6 services are resumable for normal completed artifacts and normal file-exists skips.
- Current v0.6 services do not recover from workflow-completed/artifact-missing divergence.
- Phase 7 must report any such divergence as a release readiness issue because it breaks artifact integrity and can mask missing outputs.

---

## 4. Workflow State Validation

Workflow stages to validate:

- `brief`
- `content_intelligence`
- `storyboard`
- `thumbnail`
- `script`
- `carousel`
- `newsletter`

States to validate:

- `pending`
- `completed`
- `failed`

Expected transitions:

| Stage | Initial | Success | Exception Failure | Resume Behavior |
|---|---|---|---|---|
| brief | pending | Current known asymmetry: brief file exists, workflow may remain pending | Service records failure result, but may not mark workflow failed | Existing brief file is skipped by file existence. |
| content_intelligence | pending | completed | failed | Completed stage skipped; failed stage can be retried if artifact absent and service is rerun. |
| storyboard | pending | completed | failed | Completed stage skipped; failed stage can be retried if artifact absent and service is rerun. |
| thumbnail | pending | completed | failed | Completed stage skipped; failed stage can be retried if artifact absent and service is rerun. |
| script | pending | completed | failed | Completed stage skipped; failed stage can be retried if artifact absent and service is rerun. |
| carousel | pending | completed | failed | Completed stage skipped; failed stage can be retried if artifact absent and service is rerun. |
| newsletter | pending | completed | failed | Completed stage skipped; failed stage can be retried if artifact absent and service is rerun. |

Invalid transitions to detect:

- `completed` to `pending` without explicit state reset.
- `completed` to `failed` on a later idempotent run.
- Asset `completed` when corresponding asset file is missing.
- Storyboard `completed` when storyboard file is missing.
- Content Intelligence `completed` when CI file is missing.
- Optional asset marked completed when not recommended and not generated.

Evidence collection strategy:

1. Capture `data/workflow_state/{topic_id}.json` before and after each validation run.
2. Capture artifact existence and path for each completed workflow state.
3. Compare workflow `artifact_path` to actual file existence.
4. Record transition table for every topic in the validation run.

Known release note:

- Brief workflow state should be explicitly inspected and classified according to "Brief Workflow State Classification" above. For v0.6 validation, `brief=pending` with an existing brief artifact is an accepted exception, not a release blocker by itself.

---

## 5. Artifact Lineage Validation

Objective: prove a topic maintains identity and core metadata through every stage.

Lineage path:

```text
Staged
-> Scored
-> Brief
-> Content Intelligence
-> Storyboard
-> Assets
```

Lineage checks:

- Staged topic `id` equals scored topic `id`.
- Scored topic `id` equals brief `topic_id`.
- Brief `topic_id` equals CI `topic_id`.
- CI `topic_id` equals storyboard `topic_id`.
- Storyboard `topic_id` equals every generated asset `topic_id`.
- Manifest `topic_id` equals the same topic ID.

Topic ID checks:

- No artifact uses source URL, title, or filename as substitute identity.
- Every generated artifact filename is `{topic_id}.json`.
- Every artifact body contains the same topic ID as its filename stem.

Metadata consistency checks:

- Brief `source_url` matches staged/scored URL where available.
- Asset `source_links` include the brief source URL where applicable.
- Manifest source URL matches the topic source URL.
- Recommended formats in brief map to generated optional assets or manifest skipped statuses.
- Generated timestamps exist and are parseable where models require them.

Evidence required:

- A lineage table per validation topic.
- JSON excerpts or parsed values for topic ID and source URL.
- File path list proving filename/body alignment.

---

## 6. Storyboard Ownership Validation

This is the highest-priority Phase 7 validation area.

Objective: prove assets consume Storyboard outputs, not merely Brief outputs.

Core method:

Use controlled test inputs where Brief values and Storyboard values are intentionally different. The storyboard should contain unique sentinel values that cannot be confused with brief-derived content.

Recommended sentinel pattern:

```text
brief.analogy = "BRIEF_ANALOGY_DO_NOT_USE"
brief.plain_english_summary = ["BRIEF_CLAIM_DO_NOT_USE"]
storyboard.visual_metaphor = "STORYBOARD_VISUAL_METAPHOR_USED"
storyboard.thumbnail_hook = "STORYBOARD_THUMBNAIL_HOOK_USED"
storyboard.script_hook = "STORYBOARD_SCRIPT_HOOK_USED"
storyboard.script_claims = ["STORYBOARD_SCRIPT_CLAIM_USED"]
storyboard.script_cta = "STORYBOARD_SCRIPT_CTA_USED"
storyboard.carousel_hook = "STORYBOARD_CAROUSEL_HOOK_USED"
storyboard.carousel_claims = ["STORYBOARD_CAROUSEL_CLAIM_USED"]
storyboard.carousel_cta = "STORYBOARD_CAROUSEL_CTA_USED"
storyboard.newsletter_hook = "STORYBOARD_NEWSLETTER_HOOK_USED"
storyboard.newsletter_claims = ["STORYBOARD_NEWSLETTER_CLAIM_USED"]
storyboard.newsletter_cta = "STORYBOARD_NEWSLETTER_CTA_USED"
```

### Thumbnail

Validate storyboard ownership for:

- `visual_metaphor`
- `thumbnail_hook`
- `visual_style`

Expected asset evidence:

- Thumbnail `visual_metaphor` equals storyboard `visual_metaphor`.
- Thumbnail `title_text` equals storyboard `thumbnail_hook`.
- Thumbnail `style` equals storyboard `visual_style`.
- Thumbnail output does not contain `BRIEF_ANALOGY_DO_NOT_USE` in storyboard mode.

Silent fallback detection:

- Fail validation if thumbnail `visual_metaphor` equals brief analogy.
- Fail validation if thumbnail title follows LLM/brief content instead of storyboard hook.

### Script

Validate storyboard ownership for:

- hook
- claims
- CTA
- visual metaphor in prompt influence when observable

Expected asset evidence for `short_video`:

- Script `hook` equals storyboard `script_hook`.
- Script `claims_used` equals storyboard `script_claims`.
- Script `cta` equals storyboard `script_cta`.
- Script does not use brief-only summary sentinel values as claims.

Silent fallback detection:

- Fail validation if `claims_used` contains `BRIEF_CLAIM_DO_NOT_USE`.
- Fail validation if hook or CTA does not match storyboard sentinel values.

### Carousel

Validate storyboard ownership for:

- carousel hook
- carousel claims
- carousel CTA
- visual metaphor

Expected asset evidence:

- First carousel slide title equals storyboard `carousel_hook`.
- Carousel `claims_used` equals storyboard `carousel_claims`.
- Carousel `cta_slide` equals storyboard `carousel_cta`.
- Fallback carousel visual note uses storyboard `visual_metaphor` when inference fails.

Silent fallback detection:

- Fail validation if carousel claims use brief summary.
- Fail validation if first slide title is generated from brief instead of storyboard hook.
- Fail validation if CTA does not equal storyboard CTA.

### Newsletter

Validate storyboard ownership for:

- newsletter hook
- newsletter claims
- newsletter CTA

Expected asset evidence:

- Newsletter `subject_line` equals storyboard `newsletter_hook`.
- Newsletter `claims_used` equals storyboard `newsletter_claims`.
- Newsletter `cta` equals storyboard `newsletter_cta`.
- Newsletter does not use brief summary sentinel values as claims.

Silent fallback detection:

- Fail validation if newsletter subject line is not the storyboard hook.
- Fail validation if claims contain the brief-only sentinel.
- Fail validation if CTA is not the storyboard CTA.

Prompt-level validation:

- Where tests intercept generator prompt text, verify storyboard claims replace `brief.plain_english_summary` in storyboard mode for Carousel, Newsletter, and Script.
- Verify storyboard `visual_metaphor` replaces `brief.analogy`.

Artifact-level validation:

- Compare final saved JSON assets against the storyboard JSON.
- Do not rely only on mocks or service invocation counts.
- The final release gate must include persisted asset evidence.

---

## 7. Resume & Idempotency Validation

Procedure:

1. Create isolated validation storage.
2. Run `run-pipeline --top 1`.
3. Capture:
   - File list under `data/`.
   - Content hashes for generated JSON artifacts.
   - Workflow state JSON.
   - Pipeline log path and stage summary.
4. Run `run-pipeline --top 1` again with the same inputs.
5. Capture the same evidence again.
6. Compare before and after.

Expected behavior:

- Completed stages are skipped according to workflow state and/or file existence.
- No duplicate artifacts are created.
- Topic IDs remain stable.
- Workflow state remains completed for completed stages.
- Failed states are not converted to completed unless the rerun actually regenerates the missing artifact successfully.
- Manifests may be rebuilt, but manifest count should not duplicate.

Evidence required:

- Before/after file tree.
- Before/after workflow state JSON.
- Before/after artifact hash comparison.
- Second-run pipeline log showing skipped or zero generated counts.

NO-GO conditions:

- Duplicate artifact files for the same topic and asset type.
- Completed workflow state reset to pending or failed.
- Asset content changes on second run without an intentional regeneration path.
- Second run generates assets before CI/storyboard are available.

---

## 8. Failure Injection Strategy

Controlled failures should be injected at service boundaries, not by corrupting unrelated infrastructure. The goal is to validate orchestration behavior, recovery, and evidence collection.

### ContentIntelligenceService Failure

Injection method:

- Patch or configure `ContentIntelligenceService.run()` to raise a deterministic exception.
- Alternative: patch the CI generator to raise during service execution if topic-level workflow failure behavior must be observed.

Expected behavior:

- PipelineRunService records `generate-content-intelligence` as failed.
- `pipeline_success` becomes false.
- Storyboard, Assets, and Manifests do not execute.
- Failure is exception-driven only.

Recovery behavior:

- Remove failure injection.
- Re-run pipeline.
- CI succeeds.
- Storyboard, Assets, and Manifests proceed.

Validation evidence:

- Failed run stage list.
- Pipeline log error entry.
- Absence of storyboard/assets/manifests from failed run.
- Successful rerun artifact set.

### StoryboardService Failure

Injection method:

- Patch or configure `StoryboardService.run()` to raise a deterministic exception.
- Alternative: remove matching brief for a CI artifact to validate topic-level failure without pipeline-level exception, but this must not be confused with exception-halting behavior.

Expected behavior:

- PipelineRunService records `generate-storyboards` as failed only when exception is raised.
- Assets and Manifests do not execute.
- CI artifacts remain persisted.

Recovery behavior:

- Restore StoryboardService behavior or missing dependency.
- Re-run pipeline.
- Storyboards and assets are generated.

Validation evidence:

- CI file exists after failed storyboard run.
- Storyboard stage error in pipeline log.
- No assets generated during failed run.
- Successful rerun artifacts.

### AssetGenerationService Failure

Injection method:

- Patch or configure `AssetGenerationService.run()` to raise a deterministic exception.
- Alternative: patch one generator to raise if validating per-topic workflow asset failure, but PipelineRunService only fails on service-level exception.

Expected behavior:

- PipelineRunService records `generate-assets` as failed.
- Manifest build does not execute.
- CI and storyboard artifacts remain available for recovery.

Recovery behavior:

- Remove failure injection.
- Re-run pipeline.
- Asset generation succeeds.
- Manifests build.

Validation evidence:

- Pipeline stage list ends at `generate-assets`.
- No new manifest from failed run.
- Existing CI/storyboard artifacts are reused during recovery.
- Successful asset and manifest files after rerun.

---

## 9. Manual Validation Checklist

[ ] Run the full automated test suite and confirm all tests pass.

[ ] Start validation from isolated storage or a clearly documented fixture dataset.

[ ] Execute `run-pipeline` for a single-topic happy path.

[ ] Confirm pipeline order in structured logs: collect, score, generate-briefs, generate-content-intelligence, generate-storyboards, generate-assets, build-manifests.

[ ] Confirm staged topic JSON exists.

[ ] Confirm scored topic JSON exists and contains priority score and status.

[ ] Confirm brief JSON exists for the selected topic.

[ ] Confirm content intelligence JSON exists for the same topic ID.

[ ] Confirm storyboard JSON exists for the same topic ID.

[ ] Confirm generated asset JSON files exist for required and recommended formats.

[ ] Confirm manifest JSON exists for the same topic ID.

[ ] Confirm workflow state JSON exists for the topic.

[ ] Confirm workflow state includes `content_intelligence` and `storyboard`.

[ ] Confirm completed workflow stages have existing artifact paths.

[ ] Confirm failed workflow stages are only present in controlled failure scenarios.

[ ] Confirm no duplicate artifacts are created after rerunning the pipeline.

[ ] Confirm persisted artifacts can be loaded after process restart.

[ ] Confirm asset fields use storyboard hooks, claims, CTAs, visual metaphor, and visual style.

[ ] Confirm brief-only sentinel values do not appear in storyboard-owned asset fields.

[ ] Confirm manifests reflect actual generated and skipped assets.

[ ] Confirm manifest readiness is interpreted as brief/asset readiness only, with CI/storyboard lineage checked separately.

[ ] Confirm pipeline logs contain item counts and stage statuses.

[ ] Confirm approved generator, service, and storage interfaces have not regressed.

[ ] Confirm no compatibility shims or dynamic argument remapping were introduced around generator calls.

[ ] Confirm failure injection for CI halts Storyboard, Assets, and Manifests.

[ ] Confirm failure injection for Storyboard halts Assets and Manifests.

[ ] Confirm failure injection for Assets halts Manifests.

[ ] Confirm recovery reruns complete after injected failures are removed.

[ ] Confirm workflow-completed/artifact-missing divergence is detected for CI, Storyboard, and asset stages.

[ ] Record final evidence bundle location.

---

## 10. Final Release Gate

The release gate must be evidence-based. A passing unit suite alone is not sufficient for declaring v0.6 backend architecture complete.

### GO Criteria

- Full automated suite passes from a clean test run.
- Runtime pipeline executes in this order:
  - Collect
  - Score
  - Brief
  - Content Intelligence
  - Storyboard
  - Assets
  - Manifests
- Single-topic happy path produces all expected artifacts.
- Multi-topic batch respects Top-N selection and priority ordering.
- Empty pipeline behavior is graceful and produces no invalid artifacts.
- Resume scenario completes missing downstream work without duplicating completed artifacts.
- Idempotency scenario produces no duplicate artifacts and preserves workflow state.
- Storage persistence scenario proves artifacts survive restart and reload.
- Failure injection proves exception-based halt behavior for CI, Storyboard, and Assets.
- Storyboard ownership validation proves persisted assets use storyboard-owned fields.
- Artifact lineage validates topic ID consistency across every stage.
- Brief workflow asymmetry is recorded as the accepted v0.6 exception: brief artifact existence is authoritative for brief resume behavior.
- Manifest validation proves manifest state matches generated brief/assets and does not claim CI/storyboard completion.
- Separate CI/storyboard lineage evidence exists alongside manifest readiness evidence.
- Interface contract validation confirms storyboard-first generator contracts and approved service/storage interfaces.
- Workflow/artifact divergence validation confirms completed-state/missing-artifact cases are detected and reported.
- Evidence bundle includes logs, workflow states, artifact samples, and validation notes.

### NO-GO Criteria

- Assets are generated before Content Intelligence and Storyboard in `run-pipeline`.
- Any asset silently falls back to brief-only values when a storyboard exists.
- Topic IDs diverge across any artifact lineage step.
- Workflow completed state exists while the expected artifact file is missing.
- Workflow completed state causes a missing artifact to be silently accepted in the final release evidence.
- Rerunning the pipeline creates duplicate artifacts for the same topic and stage.
- Controlled CI failure allows Storyboard, Assets, or Manifests to run.
- Controlled Storyboard failure allows Assets or Manifests to run.
- Controlled Asset failure allows Manifest build to run.
- Persisted CI or storyboard artifacts cannot be reloaded by storage APIs.
- Manifests report readiness inconsistent with actual brief/asset files.
- Release evidence treats manifest `complete` as proof of CI or Storyboard completion.
- Generator contracts regress to brief-first calls or compatibility shims.
- Release evidence is missing or not reproducible.

### Required Evidence Before Declaring v0.6 Backend Architecture Complete

- Automated test command and result summary.
- Pipeline log for happy path.
- Pipeline log for idempotency rerun.
- Pipeline logs for CI, Storyboard, and Asset failure injection.
- Artifact lineage table for at least one topic.
- Storyboard ownership comparison table for Thumbnail, Script, Carousel, and Newsletter.
- Workflow state snapshots for success, failed, and resumed scenarios.
- File tree or artifact inventory before and after idempotency rerun.
- Final manifest samples.
- Interface contract validation notes.
- Workflow/artifact divergence validation notes.
- Manual checklist with every required item checked or explicitly waived with rationale.

---

## Final Verdict

READY FOR PHASE 7 EXECUTION
