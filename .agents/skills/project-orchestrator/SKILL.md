# SKILL: project-orchestrator
## Trigger: $project-orchestrator

## PURPOSE
Quick project health check. Reads control docs, reports alignment.
Calls drift-check for the detailed analysis.

## STEPS
1. Read WORK_QUEUE.md — count DONE, PENDING, BLOCKED tasks
2. Read TASK_SPEC.md — confirm stated milestone matches queue state
3. Read docs/backlog/issues.md — count open CRITICAL and HIGH issues
4. Run $drift-check for detailed integrity analysis

## REPORT FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROJECT HEALTH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Queue:    X DONE / Y PENDING / Z BLOCKED
Phase:    <current phase from WORK_QUEUE>
Issues:   X CRITICAL / Y HIGH open
Drift:    <result from drift-check>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
