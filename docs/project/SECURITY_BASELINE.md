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
