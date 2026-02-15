# FASTAPI_BACKGROUND_WORKER_SKILL

## Purpose
Govern durable background execution patterns with idempotency, retries, DLQ handling, and worker isolation.

## Core Principles
- Separate API and worker runtime responsibilities.
- Design all jobs as idempotent.
- Use bounded retries with jittered backoff.
- Route exhausted failures to DLQ with runbooks.

## Rules & Standards

### Tool Selection
**MUST**: Use Celery for distributed durable jobs; APScheduler only for simple controlled schedules.
**MUST NOT**: Run singleton schedules in all API replicas.
**WHY**: Prevents duplicate execution in horizontal scale.
**EXAMPLE**: Celery beat single instance + dedicated workers.

### Idempotency
**MUST**: Require idempotency key per externally visible side-effect.
**MUST NOT**: Re-run payment/email actions without dedup guard.
**WHY**: At-least-once delivery is expected.
**EXAMPLE**: Redis `SETNX idempotency:{key}` with TTL.

### Retry Policy
**MUST**: Use exponential backoff with cap and jitter.
**MUST NOT**: Infinite retries.
**WHY**: Protects dependencies and controls queue growth.
**EXAMPLE**:
```python
@celery.task(bind=True, autoretry_for=(TimeoutError,), retry_backoff=True, retry_jitter=True, max_retries=5)
def sync_billing(self, invoice_id: str): ...
```

### Dead-Letter Queue
**MUST**: Route max-retry failures to DLQ and alert.
**MUST NOT**: Silently drop failed jobs.
**WHY**: Preserves auditability and recovery.
**EXAMPLE**: `jobs:dlq` stream with failure metadata.

### Worker Isolation
**MUST**: Split queues by priority and workload class.
**MUST NOT**: Share one queue for critical and batch jobs.
**WHY**: Prevents starvation and noisy neighbors.
**EXAMPLE**: `critical`, `default`, `bulk` queues with separate concurrency.

## Anti-Patterns

### ❌ Blocking Task Without Timeout
**Problem**: External call without timeout.
**Impact**: Worker slot starvation.
**Fix**: Set hard and soft time limits.
**Detection**: Scan tasks for HTTP/DB calls without timeout args.

### ❌ Unhandled Task Exception
**Problem**: Task crashes before status tracking.
**Impact**: Lost observability and orphaned side effects.
**Fix**: Wrap with standardized task instrumentation.
**Detection**: Missing task-level logging and final status emit.

## Enforcement

### Pre-commit Hooks
- Enforce timeout arguments for HTTP clients in task modules.
- Enforce idempotency key usage for marked side-effect tasks.

### CI Checks
- Retry behavior tests with transient fault simulation.
- Duplicate delivery tests assert idempotent outcomes.
- DLQ routing tests for exhausted retries.

### Manual Review
- Verify queue routing policy and concurrency allocations.
- Verify graceful shutdown and in-flight job handling.
- Verify runbooks for DLQ replay.

## Quick Reference
- Use Celery for durable distributed jobs.
- Idempotency required.
- Retries bounded with jitter.
- DLQ mandatory.
- Isolate worker queues by priority.
