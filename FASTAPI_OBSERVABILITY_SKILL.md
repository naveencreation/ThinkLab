# FASTAPI_OBSERVABILITY_SKILL

## Purpose
Enforce production-grade telemetry for fast incident triage and service-level reliability control.

## Core Principles
- Log in structured JSON with stable fields.
- Attach correlation IDs to every request and downstream call.
- Emit actionable metrics with bounded cardinality.
- Instrument latency and failures by endpoint class.

## Rules & Standards

### Structured Logging
**MUST**: Emit JSON logs with timestamp, level, service, env, trace_id, event.
**MUST NOT**: Emit free-form logs in production.
**WHY**: Enables deterministic parsing and alerting.
**EXAMPLE**:
```python
logger.info('request.complete', extra={'trace_id': trace_id, 'path': path, 'latency_ms': ms})
```

### Correlation ID
**MUST**: Generate or propagate `X-Request-ID` per request.
**MUST NOT**: Drop IDs on downstream calls.
**WHY**: Preserves end-to-end traceability.
**EXAMPLE**: Middleware sets contextvar and response header.

### Performance Logging
**MUST**: Record request latency and slow-query timing.
**MUST NOT**: Ignore p95/p99 tails.
**WHY**: Tail latency governs user experience.
**EXAMPLE**: Alert when DB query >100ms sustained.

### Prometheus Metrics
**MUST**: Expose HTTP count, duration histogram, error count, and key business counters.
**MUST NOT**: Use unbounded label cardinality (user_id, raw URL).
**WHY**: High-cardinality metrics destabilize TSDB.
**EXAMPLE**: Labels: method, route_template, status_class.

### Tracing
**MUST**: Support OpenTelemetry in distributed deployments.
**MUST NOT**: Sample 100% traces at high volume without capacity planning.
**WHY**: Controls observability cost.
**EXAMPLE**: Parent-based sampler with 5-10% baseline.

## Anti-Patterns

### ❌ Log Spam
**Problem**: Debug-level logs on every internal step in production.
**Impact**: Increased cost, noisy alerts, hidden true failures.
**Fix**: Define level policy and structured event catalog.
**Detection**: Log volume anomaly versus request volume baseline.

### ❌ High-Cardinality Labels
**Problem**: Metrics tagged with user-specific IDs.
**Impact**: Metrics backend blow-up.
**Fix**: Restrict labels to bounded enums/templates.
**Detection**: Cardinality scanner in metrics pipeline.

## Enforcement

### Pre-commit Hooks
- Block logger calls with f-string dumping full payloads.
- Enforce observability middleware presence in app startup.

### CI Checks
- Contract tests for `X-Request-ID` propagation.
- Snapshot tests for JSON log schema fields.
- Metrics endpoint smoke test and label cardinality assertions.

### Manual Review
- Validate alert rules cover error rate and latency SLOs.
- Validate PII redaction policy in formatter and processors.
- Validate sampling strategy by environment.

## Quick Reference
- JSON logs only.
- Correlation ID everywhere.
- Metrics with bounded labels.
- Latency instrumentation mandatory.
- OTel tracing supported with controlled sampling.
