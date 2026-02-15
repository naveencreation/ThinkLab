# FASTAPI_PERFORMANCE_SCALING_SKILL

## Purpose
Define hard performance and scalability rules for FastAPI services operating at sustained high throughput.

## Core Principles
- Keep request path async and non-blocking.
- Bound every query and payload.
- Optimize response shape and transfer size.
- Scale horizontally with stateless runtime.

## Rules & Standards

### Async Enforcement
**MUST**: Offload CPU-bound work to workers/executors.
**MUST NOT**: Execute blocking I/O in async handlers.
**WHY**: Preserves event loop responsiveness.
**EXAMPLE**:
```python
result = await asyncio.to_thread(sync_lib_call, payload)
```

### Pagination
**MUST**: Paginate list endpoints; default 50, max 1000 for offset, prefer cursor for large sets.
**MUST NOT**: Return unbounded collections.
**WHY**: Prevents memory and latency spikes.
**EXAMPLE**:
```python
@router.get('/items')
async def list_items(limit: int = Query(50, le=1000), cursor: str | None = None): ...
```

### Response Optimization
**MUST**: Use response models to exclude unused fields.
**MUST NOT**: Serialize full ORM graphs.
**WHY**: Reduces payload size and CPU cost.
**EXAMPLE**: `response_model=ItemSummary`.

### Compression
**MUST**: Enable GZip/Brotli for payloads >1KB with content-type allowlist.
**MUST NOT**: Compress already-compressed media.
**WHY**: Improves transfer efficiency without wasted CPU.
**EXAMPLE**: GZip middleware threshold set to 1024 bytes.

### Server Runtime
**MUST**: Run Gunicorn + Uvicorn workers in production.
**MUST NOT**: Use dev server for production traffic.
**WHY**: Provides stable process supervision and scaling.
**EXAMPLE**:
```python
# gunicorn.conf.py
workers = 2 * cpu_count() + 1
timeout = 30
graceful_timeout = 30
```

## Anti-Patterns

### ❌ Sync DB Calls in Async Route
**Problem**: Async endpoint awaits sync database function.
**Impact**: Throughput collapse and timeout chain.
**Fix**: Use async DB driver and async ORM session.
**Detection**: Static search for sync session APIs in route modules.

### ❌ Missing Pagination
**Problem**: Endpoint returns entire table.
**Impact**: OOM risk and slow responses.
**Fix**: Add cursor/offset pagination with strict max bounds.
**Detection**: Endpoint lacks `limit`/`cursor` parameters.

## Enforcement

### Pre-commit Hooks
- Block route handlers that import sync DB/HTTP clients.
- Require `limit` on list-like GET endpoints.

### CI Checks
- Load test smoke profile for p95 latency budget.
- Contract tests for pagination and response model fields.
- Verify compression middleware active in prod profile.

### Manual Review
- Verify endpoint-level SLOs and budgeted DB calls.
- Verify heavy payload endpoints use streaming where needed.
- Verify horizontal scale test evidence.

## Quick Reference
- Async-only request path.
- Pagination mandatory.
- Response models mandatory.
- Compression for textual payloads.
- Gunicorn + Uvicorn workers only.
