# FASTAPI_AGENT_SKILL.md

## FastAPI Engineering Governance Contract (Production Enforcement)

This document is a **mandatory governance baseline** for all FastAPI systems in this organization, including monoliths, microservices, SaaS platforms, internal APIs, automation systems, and AI-enabled backends.

All rules use normative language:
- **MUST / MUST NOT** = non-negotiable
- **SHOULD / SHOULD NOT** = strongly recommended, deviation requires documented approval

---

## 1) Core Architectural Principles

### 1.1 Async-First Enforcement
- All HTTP handlers **MUST** be `async def`.
- All I/O paths (DB, Redis, HTTP clients, object storage, message brokers) **MUST** use async clients.
- Blocking calls inside request lifecycle **MUST NOT** execute on the event loop.
- Any unavoidable blocking integration **MUST** be isolated behind a worker queue or threadpool boundary with explicit timeout.

### 1.2 Layered Architecture (Router → Service → Repository)
- Routing layer **MUST** only perform transport concerns (request parsing, auth dependency binding, response mapping).
- Service layer **MUST** contain business rules, orchestration, transactional intent, and domain decisions.
- Repository layer **MUST** encapsulate persistence logic and query composition.
- Cross-layer access violations (router→repository direct, repository→router references) **MUST NOT** occur.

### 1.3 Separation of Concerns
- API schemas, domain models, persistence models, and infrastructure clients **MUST** be distinct types.
- Domain logic **MUST NOT** depend on FastAPI primitives.
- Framework-specific concerns **MUST** stay at boundaries.

### 1.4 Stateless Service Design
- API instances **MUST** be stateless and horizontally replaceable.
- In-memory state for sessions, locks, counters, or shared caches **MUST NOT** be relied upon for correctness.
- Cross-instance coordination **MUST** use Redis/PostgreSQL/message infrastructure.

### 1.5 Dependency Injection Rules
- Dependencies **MUST** be explicit using FastAPI dependency injection (`Depends`).
- Service and repository wiring **MUST** be centralized in dependency modules.
- Hidden globals and implicit singletons for mutable state **MUST NOT** be used.

### 1.6 Configuration Isolation
- Configuration **MUST** be centralized in `core/config.py` (Pydantic Settings).
- Code **MUST NOT** call `os.getenv` outside the configuration module.
- Environment-specific behavior **MUST** be config-driven, never branch-specific code forks.

### 1.7 Environment-Based Settings Enforcement
- All secrets **MUST** originate from environment variables or secret managers.
- Per-environment values (DB URLs, Redis URLs, TLS flags, log level, feature flags) **MUST** be externally provided.
- Missing critical config at startup **MUST** fail fast.

---

## 2) Standard Project Structure

### 2.1 Required Modular Layout

```text
app/
  main.py
  api/
    v1/
      routers/
        health.py
        auth.py
        users.py
      dependencies.py
  services/
    auth_service.py
    user_service.py
  repositories/
    user_repository.py
  schemas/
    auth.py
    user.py
    common.py
  models/
    user.py
    base.py
  core/
    config.py
    security.py
    logging.py
    errors.py
    middleware.py
  infrastructure/
    db/
      session.py
      base.py
    redis/
      client.py
      cache.py
      locks.py
    clients/
      payment_client.py
      ai_client.py
  workers/
    celery_app.py
    tasks/
      email_tasks.py
      billing_tasks.py
  observability/
    metrics.py
    tracing.py
  tests/
    unit/
    integration/
    contract/
```

### 2.2 API Versioning Strategy
- Public APIs **MUST** be namespaced under `/api/v{n}`.
- Breaking changes **MUST** increment API version.
- Parallel support windows **MUST** be defined and time-bounded.

### 2.3 Multi-Service Scalability Guidance
- Shared libraries **MUST** be extracted to versioned internal packages, not copy-pasted modules.
- Service boundaries **MUST** map to domain ownership and data ownership.
- Cross-service synchronous dependencies **SHOULD** be minimized; asynchronous/event integration **SHOULD** be preferred for loose coupling.

---

## 3) Async Database Standards (PostgreSQL)

### 3.1 SQLAlchemy 2.0 Async Enforcement
- ORM/data access **MUST** use SQLAlchemy 2.0 async engine and async session.
- Sync SQLAlchemy sessions in API execution paths **MUST NOT** be used.

### 3.2 Session Lifecycle
- Session scope **MUST** be request-scoped by dependency.
- Session objects **MUST NOT** be stored globally.
- Session cleanup **MUST** be guaranteed via dependency teardown.

### 3.3 Transaction Boundaries
- Service methods with write operations **MUST** define explicit transaction boundaries.
- Multi-repository writes **MUST** be wrapped in a single transaction where atomicity is required.
- Implicit autocommit assumptions **MUST NOT** exist.

### 3.4 Pooling Requirements
- Connection pool size, overflow, recycle, and timeout **MUST** be explicitly configured.
- Pool exhaustion behavior **MUST** be observable via metrics and logs.

### 3.5 Migration Enforcement
- Schema changes **MUST** be managed through Alembic revisions.
- Direct manual schema edits in production **MUST NOT** occur.
- CI **MUST** validate migrations apply cleanly from base to head.

### 3.6 Query Performance Rules
- N+1 patterns **MUST NOT** exist.
- Large list queries **MUST** include pagination.
- Heavy filters **MUST** be indexed.
- Query plans for critical endpoints **SHOULD** be reviewed periodically.

### 3.7 Explicit Prohibition
- Sync DB drivers or sync DB calls in async endpoints **MUST NOT** be used.

---

## 4) Redis & Caching Standards

### 4.1 Cache-Aside Pattern
- Read-heavy cached resources **MUST** use cache-aside unless explicitly justified.
- Cache miss loading **MUST** include bounded timeout and fallback behavior.

### 4.2 TTL Enforcement
- All cache keys **MUST** have TTL.
- Non-expiring cache keys **MUST NOT** be used for dynamic data.

### 4.3 Key Namespacing Convention
- Keys **MUST** follow:
  - `<service>:<env>:<domain>:<entity>:<id>[:<suffix>]`
- Keys **MUST** avoid unbounded cardinality without eviction strategy.

### 4.4 Rate Limiting Pattern
- Public APIs **MUST** enforce Redis-backed rate limits.
- Rate limit key dimensions **MUST** include subject (`user_id` or IP), route group, and time window.

### 4.5 Distributed Locking
- Cross-instance critical sections **MUST** use Redis lock with TTL and ownership token verification.
- Lock operations **MUST** fail safely on timeout.
- Locks **MUST NOT** be used as substitute for DB integrity constraints.

### 4.6 Pub/Sub and Streams Usage
- Fire-and-forget notifications **SHOULD** use Pub/Sub.
- Durable processing **MUST** use Streams with consumer groups and explicit ACK.
- Stream consumers **MUST** have pending-entry recovery strategy.

### 4.7 Multi-Replica Consistency
- Cache invalidation on write **MUST** be deterministic.
- Read-after-write consistency expectations **MUST** be documented per endpoint.
- Critical correctness flows **MUST NOT** depend on eventually consistent cache state.

---

## 5) Authentication & Authorization Standards

### 5.1 JWT Architecture
- Authentication **MUST** use short-lived access tokens + longer-lived refresh tokens.
- Access and refresh tokens **MUST** have separate signing/audience controls where feasible.

### 5.2 Token Rotation
- Refresh token rotation **MUST** be implemented.
- Reused refresh token detection **MUST** trigger session revocation.

### 5.3 RBAC
- Authorization **MUST** enforce role/permission checks in service-level policy guards.
- Route-level coarse checks **MAY** exist, but fine-grained authorization **MUST** be service-enforced.

### 5.4 Password Hashing
- Passwords **MUST** be hashed with Argon2id or bcrypt with strong cost parameters.
- Plaintext password storage/logging **MUST NOT** occur.

### 5.5 Secret Management
- JWT keys, DB credentials, API secrets **MUST** come from environment/secret manager only.
- Secret literals in repository **MUST NOT** exist.

### 5.6 Prohibited Insecure Patterns
- Long-lived bearer tokens without rotation **MUST NOT** be used.
- Unsigned/weakly signed tokens (`alg=none`, weak shared keys) **MUST NOT** be used.

---

## 6) Error Handling Contract

### 6.1 Global Exception Handling
- Application **MUST** register global exception handlers for:
  - validation failures
  - domain errors
  - infrastructure errors
  - unknown exceptions

### 6.2 Standard Response Envelope
- Error responses **MUST** conform to stable schema:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Resource not found",
    "correlation_id": "...",
    "details": {}
  }
}
```

### 6.3 Error Code Mapping
- Domain exceptions **MUST** map deterministically to HTTP status + application error codes.
- Free-form ad hoc error strings **MUST NOT** be used as contracts.

### 6.4 Internal Error Leakage
- Stack traces, SQL text, internal hostnames, and secret-bearing context **MUST NOT** be exposed to clients.

### 6.5 Structured Error Logging
- All server errors **MUST** log structured context: correlation ID, route, principal, latency, error class.

---

## 7) Logging & Observability

### 7.1 Structured Logging
- Production logs **MUST** be JSON.
- Log lines **MUST** include timestamp, level, service, environment, correlation ID, and event name.

### 7.2 Correlation ID
- Each request **MUST** have a correlation ID (incoming propagation or generated).
- Correlation ID **MUST** be propagated to downstream HTTP/message calls.

### 7.3 Latency Logging
- Request latency **MUST** be captured and emitted.
- SLO-critical endpoint latency percentiles **MUST** be tracked.

### 7.4 Metrics
- `/metrics` endpoint **MUST** expose Prometheus metrics in production environments where observability stack exists.

### 7.5 Health Endpoints
- `/health` (process alive), `/live` (liveness), `/ready` (dependency readiness) **MUST** be implemented separately.

### 7.6 Tracing
- OpenTelemetry tracing **SHOULD** be enabled for distributed environments.
- Trace IDs **SHOULD** correlate with logs.

---

## 8) Background Jobs & Scheduling Standards

### 8.1 Tool Selection
- Celery + Redis/RabbitMQ **MUST** be used for durable, distributed async jobs.
- APScheduler **MUST NOT** run in every API replica for singleton schedules.
- In-process background tasks **MAY** be used only for non-critical, short-lived post-response work.

### 8.2 Idempotency
- Jobs **MUST** be idempotent using idempotency keys or dedup state.
- Retried jobs **MUST NOT** corrupt data.

### 8.3 Retry Strategy
- Retry policy **MUST** use bounded exponential backoff with jitter.
- Permanent failures **MUST** transition to dead-letter handling.

### 8.4 Dead-Letter Queue
- DLQ **MUST** exist for non-recoverable tasks.
- DLQ processing ownership and runbook **MUST** be documented.

### 8.5 Duplicate Execution Prevention
- Scheduled or singleton tasks **MUST** use distributed lock/lease strategy.
- Exactly-once assumptions over at-least-once systems **MUST NOT** be made without compensating controls.

### 8.6 Worker Isolation
- Workers **MUST** be isolated from API pods/processes where throughput or fault isolation matters.

---

## 9) Performance & Scalability Standards

### 9.1 Async-Only Enforcement
- Public request path **MUST** remain async end-to-end.

### 9.2 Pagination
- List endpoints returning non-trivial datasets **MUST** implement pagination (`limit`, `cursor`/`offset`).

### 9.3 Response Models
- All endpoints **MUST** declare response models.
- Raw ORM entities **MUST NOT** be returned.

### 9.4 Compression
- GZip/Brotli compression **MUST** be enabled for suitable payload sizes.

### 9.5 Worker Scaling
- Production serving **MUST** use Gunicorn with Uvicorn workers (or equivalent orchestrated process model).
- Worker count **MUST** be tuned from CPU/memory/load profiles, not defaults.

### 9.6 Horizontal Readiness
- API **MUST** tolerate multi-instance deployment with no sticky-session requirements unless explicitly justified.

---

## 10) Security Standards

### 10.1 CORS Policy
- CORS allowlist **MUST** be explicit per environment.
- Wildcard CORS in production **MUST NOT** be used for credentialed endpoints.

### 10.2 Rate Limiting
- Public and auth-sensitive endpoints **MUST** enforce rate limits.

### 10.3 Input Validation
- Request payloads **MUST** be validated via Pydantic schemas.
- Unvalidated dynamic dict ingestion **MUST NOT** bypass schema constraints.

### 10.4 Secure Headers
- Responses **MUST** set security headers (at minimum: HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, CSP where applicable).

### 10.5 TLS
- TLS termination **MUST** be enforced at ingress/proxy.
- Internal plaintext traffic across trust boundaries **MUST NOT** be accepted.

### 10.6 Container Hardening
- Docker containers **MUST** run as non-root.
- Minimal base images **SHOULD** be used.
- Shell/debug tooling **SHOULD NOT** be present in production images.

### 10.7 Secrets
- Hardcoded secrets **MUST NOT** exist in source, tests, examples, or CI logs.

---

## 11) Deployment Standards

### 11.1 Dockerfile
- Multi-stage Docker builds **MUST** be used.
- Build dependencies **MUST NOT** remain in runtime image.
- Healthcheck endpoint **MUST** be configured.

### 11.2 Production Server Runtime
- Gunicorn + `UvicornWorker` (or equivalent) **MUST** be used in production.
- Worker timeouts, keepalive, max requests, and graceful shutdown settings **MUST** be explicitly configured.

### 11.3 Reverse Proxy
- Nginx/ingress **MUST** enforce request size limits, timeout controls, TLS policy, and forwarded headers correctness.

### 11.4 Kubernetes
- Deployments **MUST** define readiness/liveness probes.
- Resource requests/limits **MUST** be set.
- Pod disruption budgets **SHOULD** be defined for critical services.

### 11.5 Zero-Downtime
- Deployments **MUST** support rolling updates with readiness gates.
- Backward compatibility during rollout windows **MUST** be guaranteed for contracts and migrations.

---

## 12) CI/CD & Testing Enforcement

### 12.1 Static Quality Gates
- `ruff` linting **MUST** pass.
- `mypy` type checks **MUST** pass for application packages.
- Security scan (dependency and secret scanning) **MUST** run in CI.

### 12.2 Pytest Standards
- Tests **MUST** be organized by `unit/`, `integration/`, and `contract/` tiers.
- Fixtures **MUST** avoid hidden global side effects.

### 12.3 Integration Testing
- CI **MUST** run integration tests against ephemeral PostgreSQL and Redis.
- Critical endpoint auth + authorization paths **MUST** be integration-tested.

### 12.4 Migration Validation
- CI **MUST** apply Alembic migrations up/down in clean ephemeral DB before merge.

### 12.5 Coverage
- Minimum line coverage **MUST** be enforced at **80%** (or stricter per service tier).
- Critical domain/service modules **MUST** maintain targeted high coverage beyond global threshold.

---

## 13) Explicit Anti-Patterns (Strictly Forbidden)

### DO NOT
- Place business logic in route handlers.
- Execute blocking I/O directly in async endpoints.
- Return ORM entities as response payloads.
- Expose unpaginated large list endpoints.
- Run singleton schedulers inside every API replica.
- Hardcode secrets, tokens, credentials, or signing keys.
- Leak internal exception details to API clients.
- Publish public APIs without rate limiting.
- Bypass service layer for direct router→repository data mutations.
- Perform schema changes outside migration tooling.

### DO
- Keep handlers thin and declarative.
- Keep business logic in services and persistence in repositories.
- Enforce explicit contracts for requests/responses/errors.
- Treat observability, security, and resilience as mandatory features.

---

## 14) AI Enforcement Checklist (Machine-Verifiable Compliance)

Use this checklist for automated review agents and architecture audits.

### 14.1 Architecture
- [ ] All route handlers are `async def`.
- [ ] Router modules contain no business rules (heuristic: service calls only).
- [ ] Repository usage occurs only inside service/repository layers.
- [ ] API paths are versioned under `/api/v1` (or higher).

### 14.2 Database
- [ ] SQLAlchemy async engine/session configured.
- [ ] No sync DB driver usage in request handlers.
- [ ] Alembic migration directory exists and head revision is applied in CI.
- [ ] List queries include pagination parameters.

### 14.3 Redis
- [ ] Cache keys have TTL.
- [ ] Key namespace pattern enforced.
- [ ] Rate limiter exists for public endpoints.
- [ ] Distributed lock implementation uses TTL + ownership release checks.
- [ ] Streams consumers ACK messages and handle pending entries.

### 14.4 Security/Auth
- [ ] Access + refresh token flow present.
- [ ] Refresh token rotation present.
- [ ] RBAC checks implemented in service layer.
- [ ] No hardcoded secrets detected by scanner.
- [ ] CORS allowlist is explicit (no unrestricted wildcard for credentials).

### 14.5 Reliability/Observability
- [ ] Global exception handlers registered.
- [ ] Standard error envelope enforced.
- [ ] Correlation ID middleware present.
- [ ] JSON structured logging enabled in production profile.
- [ ] `/health`, `/live`, `/ready`, `/metrics` endpoints available.

### 14.6 Deployment/Runtime
- [ ] Multi-stage Dockerfile present.
- [ ] Container runs as non-root.
- [ ] Gunicorn + UvicornWorker production command configured.
- [ ] Readiness/liveness probes configured in deployment manifests.

### 14.7 CI/CD Quality Gates
- [ ] `ruff` pass required.
- [ ] `mypy` pass required.
- [ ] `pytest` unit + integration suites executed.
- [ ] Coverage threshold >= 80% enforced.
- [ ] Migration validation step required before merge.

---

## Enforcement Clause

Any deviation from this contract **MUST** include:
1. Written architectural exception proposal,
2. Risk assessment,
3. Expiration date,
4. Explicit approval from designated platform/backend owners.

Unapproved deviations are non-compliant and **MUST** block merge/release.
