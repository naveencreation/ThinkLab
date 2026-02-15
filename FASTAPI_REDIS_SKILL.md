# FASTAPI_REDIS_SKILL

## Purpose
Standardize Redis usage for caching, coordination, and messaging with strict TTL, namespacing, and failure handling.

## Core Principles
- Treat Redis as a distributed system boundary, not local memory.
- Require TTL for all cache keys.
- Use deterministic key naming and invalidation.
- Design for replica lag and transient failures.

## Rules & Standards

### Cache-Aside
**MUST**: Implement read path as cache lookup → DB fallback → cache set with TTL.
**MUST NOT**: Return stale cache forever.
**WHY**: Balances speed and correctness.
**EXAMPLE**:
```python
async def get_user(uid: str):
    key = f"prod:api:user:v1:{uid}"
    if val := await redis.get(key): return json.loads(val)
    row = await repo.get_user(uid)
    await redis.set(key, row.model_dump_json(), ex=300)
    return row
```

### Key Namespacing
**MUST**: Use `<env>:<service>:<domain>:v<schema>:<id>`.
**MUST NOT**: Use ambiguous flat keys.
**WHY**: Prevents collisions and simplifies migrations.
**EXAMPLE**: `prod:api:session:v2:token:abc123`.

### TTL Enforcement
**MUST**: Set TTL on every cache key.
**MUST NOT**: Use infinite TTL in production.
**WHY**: Prevents stale-data lock-in and memory bloat.
**EXAMPLE**: 30s–5m for hot reads; 15m for low-volatility config.

### Distributed Locking
**MUST**: Use lock with lease TTL + token ownership verification.
**MUST NOT**: Release lock without ownership check.
**WHY**: Prevents cross-worker corruption.
**EXAMPLE**:
```python
@asynccontextmanager
async def redis_lock(name: str, ttl_s: int = 10):
    token = secrets.token_hex(16)
    ok = await redis.set(name, token, ex=ttl_s, nx=True)
    if not ok: raise LockBusy()
    try: yield
    finally:
        await redis.eval("if redis.call('get',KEYS[1])==ARGV[1] then return redis.call('del',KEYS[1]) end",1,name,token)
```

### Rate Limiting
**MUST**: Enforce distributed limiter for public endpoints.
**MUST NOT**: Depend on per-process counters.
**WHY**: Guarantees fairness across replicas.
**EXAMPLE**: Sliding-window sorted-set or token-bucket script.

### Streams and Pub/Sub
**MUST**: Use Streams for durable workflows with ACK and retry policy.
**MUST NOT**: Use Pub/Sub for guaranteed delivery.
**WHY**: Pub/Sub loses messages when consumers disconnect.
**EXAMPLE**: `XREADGROUP` + pending recovery + DLQ.

## Anti-Patterns

### ❌ Cache Stampede
**Problem**: Many misses hit DB simultaneously.
**Impact**: DB overload and cascading timeouts.
**Fix**: Add jittered TTL and single-flight lock.
**Detection**: Burst miss rate + DB spike on same key family.

### ❌ Missing TTL
**Problem**: Cache key without expiration.
**Impact**: Staleness and memory growth.
**Fix**: Enforce `ex`/`px` in wrappers.
**Detection**: CI grep for `set(` without expiry in cache modules.

## Enforcement

### Pre-commit Hooks
- Reject Redis set calls in cache modules lacking TTL args.
- Validate key names include env/service/version prefix.

### CI Checks
- Integration tests for cache hit/miss/invalidate.
- Lock acquisition/release ownership tests.
- Rate-limit consistency tests across concurrent workers.

### Manual Review
- Verify cache invalidation at write path.
- Verify stream consumers ACK and retry boundedly.
- Verify public endpoints have limiter coverage.

## Quick Reference
- Cache-aside only.
- TTL mandatory.
- Namespaced keys mandatory.
- Use Streams for durability.
- Use ownership-checked distributed locks.
