# SKILL: security-audit
## Trigger: `$security-audit`

Read this file completely before executing.
This skill is READ-ONLY. It changes nothing.

---

## PURPOSE

Run a local security scan and produce findings.
Covers: committed secrets, secret loading patterns, gitignore gaps, agent file risks.

---

## EXECUTION SEQUENCE

### Step 1 — Git history scan

```bash
# Scan for Gemini API key patterns in full history
git log --all --full-diff -p -- "*.py" "*.yaml" "*.yml" "*.env" "*.json" \
  | grep -E "AIza[A-Za-z0-9_-]{20,}" | head -20

# Check if .env was ever committed
git log --all --oneline -- .env

# Check for sk- patterns (OpenAI/generic)
git log --all -p | grep -E "sk-[a-zA-Z0-9]{20,}" | head -10
```

Note findings. Do NOT print the actual key values if found — print only the
file path and commit hash.

---

### Step 2 — Working tree scan

```bash
# Check for non-empty fallbacks on environment variable reads
grep -rn 'os\.environ\.get.*"[A-Za-z]' src/ --include="*.py" | \
  grep -v "# test" | grep -v "test_" | head -20

# Check for import-time secret reading (dangerous pattern)
grep -rn 'API_KEY\s*=\s*os\.' src/ --include="*.py" | head -20

# Check config files for embedded values
grep -rn "AIza\|Bearer \|sk-\|api_key:" config/ prompts/ docs/ --include="*.yaml" --include="*.yml" --include="*.md" | head -20

# Check agent instruction files
grep -rn "AIza\|GEMINI_API_KEY\|api_key" .claude/ .github/agents/ .codex/ 2>/dev/null | head -20
```

---

### Step 3 — Gitignore coverage check

```bash
# Test that .env is ignored
git check-ignore -v .env && echo ".env: IGNORED (good)" || echo ".env: NOT IGNORED (bad)"

# Test database file coverage
for f in jobs.db events.db audit.db metrics.db app.db; do
  git check-ignore -v "$f" && echo "$f: IGNORED" || echo "$f: NOT IGNORED — RISK"
done

# Test that data/ is ignored
git check-ignore -v data/test.json && echo "data/: IGNORED (good)" || echo "data/: NOT IGNORED (bad)"
```

---

### Step 4 — Check .env.example exists

```bash
test -f .env.example && echo ".env.example: EXISTS (good)" || echo ".env.example: MISSING (bad)"
```

---

### Step 5 — Check for pre-commit hooks

```bash
test -f .pre-commit-config.yaml && echo "pre-commit: CONFIGURED (good)" || echo "pre-commit: NOT CONFIGURED (risk)"
test -d .github/workflows && ls .github/workflows/ || echo "GitHub Actions: NO WORKFLOWS (risk)"
```

---

### Step 6 — Produce security scan report

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
$security-audit REPORT
Date: <today>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SCAN 1 — Git History:      CLEAN | FINDINGS (<count>)
SCAN 2 — Working Tree:     CLEAN | FINDINGS (<count>)
SCAN 3 — Gitignore:        ADEQUATE | GAPS (<list>)
SCAN 4 — .env.example:     EXISTS | MISSING
SCAN 5 — Pre-commit/CI:    CONFIGURED | NOT CONFIGURED

━━ FINDINGS ━━━━━━━━━━━━━━━━━━━━━━━━

[List each finding with: location, what was found, severity]
[Never print the actual secret value — only the location]

━━ CLEAN ITEMS ━━━━━━━━━━━━━━━━━━━━━

[List what was scanned and found clean]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

If CRITICAL findings are found (actual committed secrets):
- Immediately state: "ROTATE THIS KEY NOW — do not wait"
- Reference the exact commit hash where the key appeared
- Do not attempt to fix — only report

---

## WHAT NOT TO DO

- Do NOT print actual secret values in output
- Do NOT attempt to fix findings — only report
- Do NOT modify .gitignore, source files, or any file
- Do NOT commit anything
