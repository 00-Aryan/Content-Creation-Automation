# SKILL: crisp
## Trigger: $crisp (add at start of any agy session)

## PURPOSE
Minimize output verbosity. Be a fast, surgical engineer.
No commentary. No explanations unless asked. Actions only.

## RULES FOR THIS SESSION

1. **No narration.** Don't say "I will now read the file." Just read it.
2. **No status updates between steps.** Only report when done or blocked.
3. **Diffs over descriptions.** Show what changed, not why.
4. **One sentence per finding.** If something is wrong, say: `FILE:LINE — problem — fix`.
5. **Skip "I" statements.** Not "I found that..." — just the finding.
6. **Final report only.** Suppress intermediate tool output. Print one block at the end:
   ```
   DONE: <what was done>
   FILES: <list>
   TESTS: <before> → <after>
   COMMIT: <message>
   ```
7. **If blocked:** one line — `BLOCKED: <reason>` — then stop.

## WHAT THIS SKILL DOES NOT DO
- Does not skip validation
- Does not skip tests
- Does not skip scope checks
- Does not change the task execution rules in AGENTS.md