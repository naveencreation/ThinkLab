# FASTAPI_DEPLOYMENT_DEVOPS_SKILL

## Purpose
Standardize secure, repeatable, zero-downtime deployment and CI/CD operations for FastAPI services.

## Core Principles
- Build immutable non-root images.
- Validate config at startup and fail fast.
- Deploy with health-gated rolling updates.
- Block release on quality and security gates.

## Rules & Standards

### Dockerfile Standards
**MUST**: Use multi-stage build and run as non-root user.
**MUST NOT**: Ship build toolchain in runtime image.
**WHY**: Reduces attack surface and image size.
**EXAMPLE**:
```dockerfile
FROM python:3.11-slim AS runtime
RUN useradd -u 10001 appuser
USER appuser
CMD ["gunicorn","-k","uvicorn.workers.UvicornWorker","app.main:app"]
```

### Configuration
**MUST**: Read all runtime configuration from environment variables.
**MUST NOT**: Define default production secrets.
**WHY**: Supports 12-factor and safe rotation.
**EXAMPLE**: Pydantic Settings validation in startup event.

### Health Checks
**MUST**: Expose `/health` and `/ready`; readiness must verify DB/Redis connectivity.
**MUST NOT**: Use liveness endpoint for dependency checks.
**WHY**: Prevents restart storms.
**EXAMPLE**: `/health` process-only, `/ready` dependency probes.

### Reverse Proxy
**MUST**: Enforce TLS termination, body size limits, and timeout policy in ingress/Nginx.
**MUST NOT**: Trust forwarded headers without explicit configuration.
**WHY**: Prevents spoofing and resource abuse.
**EXAMPLE**:
```nginx
client_max_body_size 2m;
proxy_read_timeout 30s;
```

### CI/CD Pipeline
**MUST**: Run ruff, mypy, tests, migration validation, and image scan.
**MUST NOT**: Merge when any critical gate fails.
**WHY**: Stops production regressions early.
**EXAMPLE**:
```yaml
- run: ruff check . && mypy app
- run: pytest -q --cov=app --cov-fail-under=80
- run: alembic upgrade head
```

## Anti-Patterns

### ❌ Running as Root
**Problem**: Container uses root UID.
**Impact**: Privilege escalation blast radius.
**Fix**: Enforce non-root in Dockerfile and policy.
**Detection**: CI check inspects image user metadata.

### ❌ Untested Migrations
**Problem**: Migration merged without apply/downgrade test.
**Impact**: Deployment failure and rollback risk.
**Fix**: Add migration validation job.
**Detection**: CI required step for Alembic round-trip.

## Enforcement

### Pre-commit Hooks
- Validate Dockerfile contains non-root user.
- Validate required deployment manifests exist.

### CI Checks
- Trivy/Snyk image scan with fail thresholds.
- K8s manifest lint + schema validation.
- Rollout strategy check for zero-downtime settings.

### Manual Review
- Verify readiness probe reflects real dependencies.
- Verify HPA/resource requests set from baseline load tests.
- Verify rollback and canary strategy documented.

## Quick Reference
- Multi-stage non-root images.
- Env-only configuration.
- Health/readiness separation.
- Strict CI gates incl. migration and security scans.
- Rolling deployments only.
