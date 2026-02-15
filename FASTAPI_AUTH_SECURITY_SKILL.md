# FASTAPI_AUTH_SECURITY_SKILL

## Purpose
Enforce non-negotiable authentication, authorization, and API hardening rules for internet-exposed FastAPI services.

## Core Principles
- Keep access tokens short-lived and scoped.
- Rotate refresh tokens on every refresh.
- Enforce permission checks, not role labels alone.
- Store and rotate secrets outside source control.

## Rules & Standards

### JWT Strategy
**MUST**: Use access token TTL ≤ 15 minutes and refresh tokens with rotation.
**MUST NOT**: Issue long-lived unrotated bearer tokens.
**WHY**: Minimizes credential replay window.
**EXAMPLE**:
```python
access_exp = now + timedelta(minutes=15)
refresh_exp = now + timedelta(days=7)
```

### Refresh Rotation + Revocation
**MUST**: Invalidate previous refresh token on refresh.
**MUST NOT**: Accept reused refresh tokens.
**WHY**: Detects token theft and session hijack.
**EXAMPLE**: Track `jti` in Redis denylist/set with expiry.

### Password Security
**MUST**: Hash using Argon2id or bcrypt.
**MUST NOT**: Use SHA/MD5 for password hashing.
**WHY**: Prevents offline cracking from leaked hashes.
**EXAMPLE**:
```python
hash = pwd_context.hash(password)
pwd_context.verify(plain, hash)
```

### RBAC/Permission Guard
**MUST**: Enforce permissions in dependencies/services.
**MUST NOT**: Rely on frontend-only authorization.
**WHY**: Server is source of truth.
**EXAMPLE**:
```python
def require_perm(perm: str):
    async def dep(user=Depends(get_current_user)):
        if perm not in user.permissions: raise HTTPException(403)
    return dep
```

### API Hardening
**MUST**: Apply strict CORS allowlist, rate limiting, secure headers, and body size limits.
**MUST NOT**: Use `*` origins with credentials.
**WHY**: Reduces exploit surface.
**EXAMPLE**: HSTS + CSP + X-Frame-Options + request max size at proxy.

## Anti-Patterns

### ❌ JWT in URL Query
**Problem**: Token passed in URL params.
**Impact**: Token leakage via logs/referrers.
**Fix**: Use Authorization header only.
**Detection**: Search for `token=` in route signatures/log lines.

### ❌ Secrets in Code
**Problem**: Hardcoded JWT secret or API key.
**Impact**: Immediate credential compromise risk.
**Fix**: Read from environment/secret manager only.
**Detection**: Secret scanner + regex gates in CI.

## Enforcement

### Pre-commit Hooks
- Secret scan (`gitleaks`/equivalent).
- Reject weak JWT key length (<32 bytes).

### CI Checks
- Integration tests for login/refresh/reuse-revocation.
- Permission matrix tests (allow/deny).
- CORS and security header assertions.

### Manual Review
- Verify token claims: `sub`, `jti`, `exp`, `iat`, `scope`.
- Verify refresh rotation and denylist eviction with TTL.
- Verify no credential material is logged.

## Quick Reference
- Access ≤15m.
- Rotate refresh every use.
- Permission checks server-side.
- Argon2id/bcrypt only.
- No hardcoded secrets, ever.
