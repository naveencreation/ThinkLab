# FASTAPI_AI_COMPLIANCE_CHECKLIST

## Purpose
Define machine-verifiable governance checks and scoring for automated FastAPI repository compliance audits.

## Core Principles
- Fail fast on security/data-integrity violations.
- Score reproducibly with deterministic rules.
- Keep checks CI-ready and automatable.
- Require evidence for every pass decision.

## Rules & Standards

### Validation Rules
**MUST**: Validate architecture boundaries, auth controls, async I/O, migrations, observability, and deployment safety.
**MUST NOT**: Mark compliance without objective evidence.
**WHY**: Prevents subjective review drift.
**EXAMPLE**: CI parser checks imports and endpoint signatures.

### Code Smell Detection
**MUST**: Flag blocking calls in async handlers, missing global exception handlers, and hardcoded credentials.
**MUST NOT**: Ignore critical findings.
**WHY**: These are production incident precursors.
**EXAMPLE**: Regex/static AST checks for `time.sleep`, `requests.` in async code.

### Repository Audit
**MUST**: Verify required files exist (`Dockerfile`, `.env.example`, Alembic config, tests).
**MUST NOT**: Approve missing deployment/migration artifacts.
**WHY**: Missing operational files block safe deployment.
**EXAMPLE**: CI script checks file presence and schema.

### Compliance Scoring
**MUST**: Use weighted scoring with critical blockers.
**MUST NOT**: Average out critical failures.
**WHY**: Security/integrity cannot be offset by style points.
**EXAMPLE**: Critical=0 tolerance, High/Medium weighted totals.

## Anti-Patterns

### ❌ Compliance Without Evidence
**Problem**: Checklist says pass but no CI artifact.
**Impact**: False confidence and release risk.
**Fix**: Require artifact links for every control.
**Detection**: Missing artifact references in report JSON.

### ❌ Ignoring Critical Findings
**Problem**: Build succeeds despite secret leak finding.
**Impact**: Immediate compromise risk.
**Fix**: Critical findings force hard fail.
**Detection**: CI policy gate with severity threshold.

## Enforcement

### Pre-commit Hooks
```yaml
repos:
  - repo: local
    hooks:
      - id: ai-checklist-scan
        name: AI compliance static scan
        entry: python scripts/ai_static_scan.py
        language: system
```

### CI Checks
```yaml
name: compliance
on: [pull_request]
jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: python scripts/ai_repo_audit.py --out compliance.json
      - run: python scripts/ai_score_gate.py --report compliance.json --min-score 80
```

### Manual Review
- Confirm critical issues count is zero.
- Confirm architecture boundary violations are zero.
- Confirm all required artifacts are attached.

## Quick Reference
- Critical findings = immediate fail.
- Minimum score = 80 with zero criticals.
- Evidence required for every rule.
- CI automation is mandatory.

## JSON Schema for Compliance Report
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["repo", "timestamp", "score", "summary", "findings"],
  "properties": {
    "repo": {"type": "string"},
    "timestamp": {"type": "string", "format": "date-time"},
    "score": {"type": "number", "minimum": 0, "maximum": 100},
    "summary": {
      "type": "object",
      "required": ["critical", "high", "medium", "low"],
      "properties": {
        "critical": {"type": "integer", "minimum": 0},
        "high": {"type": "integer", "minimum": 0},
        "medium": {"type": "integer", "minimum": 0},
        "low": {"type": "integer", "minimum": 0}
      }
    },
    "findings": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "severity", "rule", "status", "evidence"],
        "properties": {
          "id": {"type": "string"},
          "severity": {"enum": ["critical", "high", "medium", "low"]},
          "rule": {"type": "string"},
          "status": {"enum": ["pass", "fail", "waived"]},
          "evidence": {"type": "array", "items": {"type": "string"}}
        }
      }
    }
  }
}
```

## Scoring Algorithm
```text
If critical_failures > 0 => score = 0 and FAIL.
Else:
  base = 100
  score = base - (high*8 + medium*3 + low*1)
  floor at 0
PASS if score >= 80.
```

## AI Prompt for Automated Review
```text
Audit this FastAPI repository using FASTAPI_*_SKILL.md governance files.
Return JSON matching the compliance schema.
Rules:
1) Zero tolerance for critical findings.
2) Include file-path evidence for each failed rule.
3) Compute score using mandated algorithm.
4) Output FAIL if score < 80 or any critical finding exists.
```
