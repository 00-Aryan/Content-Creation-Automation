# GEMINI.md - Project Instructions

## Project Overview
`content-creation` is an editorial-first content pipeline. Our goal is high-quality educational material for ML/AI students grounded in technical sources.

## Strategic Mandates
- **Branch Discipline:** Respect the branch scope. Do not modify files outside your current feature's responsibility.
- **Schema Integrity:** Do not change fields in `docs/schema.md` without an explicit directive.
- **Anti-Assumption:** If data is missing or a requirement is unclear, ask. Do not guess or hallucinate.
- **Output Validation:** After every task, provide a summary of what was updated and how it was verified.

## Priority Files
1. `docs/project-context.md`
2. `docs/schema.md`
3. `docs/branching-strategy.md`

## Engineering Standards
- Follow the Plan-Act-Validate cycle.
- Use surgical `replace` calls; avoid overwriting large files unless creating them.
- Ensure all implementation is traceable back to the requirements in `content-factory-implementation-plan.md`.
- Focus on Week 1 tasks: collectors, normalization, and CLI stubs.

## Security Constraints
- Never print, echo, log, or include any environment variable value in output
- Never run `printenv`, `env`, `echo $VARIABLE`, or equivalent commands
- Never include API keys or tokens in commit messages, branch names, or files
- If you encounter a credential in any file, stop and report its location without printing the value
