# FASTAPI_ARCHITECTURE_SKILL

## Purpose
Enforce a single production architecture for FastAPI systems: Router → Service → Repository with strict module boundaries.

## Core Principles
- Keep request handlers thin; place business rules in services.
- Preserve unidirectional dependency flow: router → service → repository.
- Enforce stateless runtime behavior across replicas.
- Use dependency injection as the only construction mechanism.
- Version all external APIs under `/api/v1` or newer.

## Rules & Standards

### Layered Architecture
**MUST**: Route handlers only parse input, invoke services, and return response DTOs.
**MUST NOT**: Put business logic, SQL, or Redis operations in routers.
**WHY**: Prevents coupling and enables deterministic reviews.
**EXAMPLE**:
```python
@router.post('/users', response_model=UserOut)
async def create_user(payload: UserCreate, svc: UserService = Depends(get_user_service)):
    return await svc.create_user(payload)
```

### Dependency Injection
**MUST**: Construct services and repositories through `Depends()` factories.
**MUST NOT**: Instantiate repositories inside route handlers.
**WHY**: Enables test-time substitution and lifecycle control.
**EXAMPLE**:
```python
def get_user_service(repo: UserRepository = Depends(get_user_repo)) -> UserService:
    return UserService(repo)
```

### Project Structure
**MUST**: Follow feature-capable layered structure shown below.
**MUST NOT**: Mix transport, domain, and persistence code in one module.
**WHY**: Scales to 50+ endpoints and multiple squads.
**EXAMPLE**:
```text
app/
  api/v1/routers/
  services/
  repositories/
  models/
  schemas/
  core/
  infrastructure/
  tests/
```

### API Versioning
**MUST**: Expose public endpoints under `/api/v1/...`.
**MUST NOT**: Ship unversioned public endpoints.
**WHY**: Enables backward-compatible change management.
**EXAMPLE**:
```python
app.include_router(v1_router, prefix='/api/v1')
```

### Stateless Design
**MUST**: Store sessions, locks, and shared state in external systems.
**MUST NOT**: Rely on process memory for correctness.
**WHY**: Guarantees horizontal scaling and safe rolling restarts.
**EXAMPLE**: Session and lock state stored in Redis.

## Anti-Patterns

### ❌ Business Logic in Router
**Problem**: Route computes pricing and performs writes directly.
**Impact**: Duplicated logic, broken tests, hidden transactions.
**Fix**: Move rules to service layer and keep router orchestration-only.
**Detection**: Router contains loops/condition-heavy logic or SQL calls.

### ❌ Circular Dependency DI Graph
**Problem**: Service A requires Service B and vice versa.
**Impact**: Runtime failures and untestable construction.
**Fix**: Extract shared policy/service boundary.
**Detection**: Import cycle or recursive DI providers.

### ❌ God Service Object
**Problem**: One service handles unrelated domains.
**Impact**: High blast radius and stalled refactors.
**Fix**: Split by bounded context.
**Detection**: Service >500 LOC with unrelated methods.

## Enforcement

### Pre-commit Hooks
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.1
    hooks: [{id: ruff}, {id: ruff-format}]
```

### CI Checks
- Fail PR if router imports repository modules.
- Fail PR if endpoint path lacks `/api/v\d+` prefix.
- Fail PR if new public route has no response model.

### Manual Review
- Verify each router method calls exactly one service entrypoint.
- Verify no infrastructure clients are imported in routers.
- Verify deprecation headers for breaking-version migrations.

## Quick Reference
- Use Router → Service → Repository.
- Version APIs under `/api/v1`.
- Keep runtime stateless.
- Inject dependencies; never construct in handlers.
- Block architecture boundary violations in CI.

## Version Migration Checklist
- Add `/api/v2` router and keep `/api/v1` stable.
- Add `Deprecation` and `Sunset` headers on v1 endpoints.
- Publish migration notes and contract tests for both versions.
