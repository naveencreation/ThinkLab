# FASTAPI_ERROR_HANDLING_SKILL

## Purpose
Enforce a deterministic, non-leaky error contract with structured logging and machine-parseable error codes.

## Core Principles
- Centralize exception handling.
- Return stable error envelopes.
- Never leak internals to clients.
- Always attach trace/correlation context.

## Rules & Standards

### Global Exception Handlers
**MUST**: Register handlers for validation, domain, infrastructure, and unexpected errors.
**MUST NOT**: Let uncaught exceptions surface raw details.
**WHY**: Preserves API contract stability.
**EXAMPLE**:
```python
app.add_exception_handler(DomainError, handle_domain_error)
app.add_exception_handler(RequestValidationError, handle_validation_error)
app.add_exception_handler(Exception, handle_unexpected)
```

### Standard Error Schema
**MUST**: Return canonical structure with `code`, `message`, `trace_id`.
**MUST NOT**: Return ad hoc strings.
**WHY**: Enables predictable client behavior.
**EXAMPLE**:
```json
{"error":{"code":"USER_NOT_FOUND","message":"User not found","trace_id":"...","retryable":false}}
```

### Error Code Taxonomy
**MUST**: Map each domain error to one code and HTTP status.
**MUST NOT**: Reuse codes for unrelated failures.
**WHY**: Avoids ambiguous operational signals.
**EXAMPLE**: `AUTH_INVALID_CREDENTIALS -> 401`, `RATE_LIMITED -> 429`.

### Structured Logging
**MUST**: Log error class, route, principal, trace_id, and latency.
**MUST NOT**: Log plaintext passwords, tokens, or card data.
**WHY**: Supports forensics without privacy breach.
**EXAMPLE**: JSON log record with redacted payload fields.

## Anti-Patterns

### ❌ Exposing Stack Traces to Clients
**Problem**: Raw traceback in response.
**Impact**: Information disclosure and exploit aid.
**Fix**: Map to generic internal error message.
**Detection**: Integration test asserts no traceback tokens in body.

### ❌ Generic 500 Without Context
**Problem**: Error response lacks code and trace ID.
**Impact**: Untriageable incidents.
**Fix**: Enforce error envelope middleware/handler.
**Detection**: API contract tests for error schema.

## Enforcement

### Pre-commit Hooks
- Reject direct `traceback.format_exc()` in responses.
- Enforce custom exception imports in API modules.

### CI Checks
- Contract tests for error payload schema.
- Snapshot tests for representative domain errors.
- Verify trace ID inclusion on 4xx/5xx responses.

### Manual Review
- Validate code-to-status mapping table coverage.
- Validate retryable flags for transient infra failures.
- Validate PII redaction policy in logger formatter.

## Quick Reference
- Handle globally.
- Return canonical error envelope.
- Map codes deterministically.
- Never leak internals.
- Include trace ID in every error.
