# FASTAPI_DATABASE_SKILL

## Purpose
Enforce async SQLAlchemy 2.0 + Alembic standards for PostgreSQL with explicit transactions and measurable performance.

## Core Principles
- Use async engine/session only.
- Control transactions explicitly in service layer.
- Require migration discipline for every schema change.
- Tune pool sizing from workload, not defaults.

## Rules & Standards

### Async Session Factory
**MUST**: Use `create_async_engine` and `async_sessionmaker`.
**MUST NOT**: Use sync sessions in request paths.
**WHY**: Prevents event-loop blocking and dead throughput.
**EXAMPLE**:
```python
engine = create_async_engine(DB_URL, pool_pre_ping=True, pool_size=20, max_overflow=20)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
async def get_db():
    async with SessionLocal() as session:
        yield session
```

### Transaction Boundaries
**MUST**: Start/commit/rollback inside service operations.
**MUST NOT**: Implicitly rely on autocommit behavior.
**WHY**: Preserves atomicity and deterministic failure handling.
**EXAMPLE**:
```python
async with session.begin():
    await repo.insert_user(session, user)
    await repo.insert_audit(session, audit)
```

### Transaction Decorator
**MUST**: Use one transaction wrapper style across services.
**MUST NOT**: Mix ad hoc commit patterns.
**WHY**: Standardization reduces write-path defects.
**EXAMPLE**:
```python
def transactional(fn):
    async def wrapper(self, *a, **kw):
        try:
            async with self.session.begin():
                return await fn(self, *a, **kw)
        except Exception:
            await self.session.rollback()
            raise
    return wrapper
```

### Pooling Standards
**MUST**: Set `pool_size`, `max_overflow`, `pool_timeout`, `pool_pre_ping`.
**MUST NOT**: Leave pool configuration undefined in production.
**WHY**: Avoids starvation and stale connections.
**EXAMPLE**: `pool_size = ceil((workers * max_inflight_db_calls) / 2)`.

### Alembic Governance
**MUST**: Commit migration with every schema change.
**MUST NOT**: Modify DB schema manually in prod.
**WHY**: Protects reproducibility and rollback.
**EXAMPLE**:
```bash
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

### Query Performance
**MUST**: Eliminate N+1 with `selectinload`/`joinedload`.
**MUST NOT**: Ship unbounded list queries.
**WHY**: Keeps p95 latency under control.
**EXAMPLE**:
```python
stmt = select(User).options(selectinload(User.roles)).limit(limit).offset(offset)
```

## Anti-Patterns

### ❌ Sync Query in Async Endpoint
**Problem**: Calls sync session in `async def` route.
**Impact**: Event loop stalls, request collapse under load.
**Fix**: Replace with async engine/session.
**Detection**: `Session()`/`.query()` usage in async modules.

### ❌ Missing FK Index
**Problem**: Foreign key column has no index.
**Impact**: Slow joins and lock amplification.
**Fix**: Add index migration.
**Detection**: Schema audit for FK columns without btree index.

## Enforcement

### Pre-commit Hooks
- Block `session.query(` and legacy SQLAlchemy query API.
- Enforce migration file presence for model changes.

### CI Checks
```bash
python -m pytest tests/integration/db
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

### Manual Review
- Verify service owns transaction boundary.
- Verify list endpoints paginate and project fields.
- Verify indexes exist for FK and high-selectivity filters.

## Quick Reference
- Async SQLAlchemy 2.0 only.
- Explicit transactions in services.
- Alembic for every schema change.
- Pool settings required.
- N+1 and unbounded queries are release blockers.
