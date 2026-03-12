# Security Best Practices
Source: supercent-io/skills-template · https://skills.sh/supercent-io/skills-template/security-best-practices
License: MIT

## Overview

Security is not a feature — it is a baseline. These rules apply to every endpoint,
every input boundary, and every piece of data that moves through the system.

## Input Validation

- Validate at the boundary — before any business logic runs
- Whitelist allowed values; reject everything else
- Never trust client-supplied IDs for authorization checks — verify ownership server-side
- Maximum lengths on all string inputs (prevent memory exhaustion)

```python
# Python/Pydantic — validation at the boundary
class ItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
```

## Authentication & Authorization

- Never roll custom auth — use established libraries (FastAPI + python-jose, axum-login, etc.)
- JWT: verify signature, expiry (`exp`), and audience (`aud`) on every request
- Never put sensitive data in JWT payload (it is base64, not encrypted)
- Authorization: check ownership on every resource access, not just at route level

```python
# Good: explicit ownership check
async def get_item(item_id: UUID, current_user: User, db: Session):
    item = db.get(Item, item_id)
    if not item or item.owner_id != current_user.id:
        raise HTTPException(status_code=404)  # 404, not 403 — do not reveal existence
    return item
```

## Secrets Management

- No secrets in code — use environment variables
- No secrets in logs — sanitize before logging
- No secrets in version control — `.env` in `.gitignore`, always
- Rotate secrets on suspected compromise — never reuse

## SQL and Injection

- Always use parameterized queries or ORM — never string interpolation in queries
- Validate that IDs are UUIDs before querying (reject non-UUID format immediately)

## HTTP Headers

```python
# Minimum security headers for all responses
headers = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'",
}
```

## Logging

```python
# Never log
logger.info(f"User logged in: {user.email} with password {password}")  # BAD

# Log this instead
logger.info(f"User logged in: user_id={user.id}")  # GOOD — no PII, no credentials
```

## Rate Limiting

- All public endpoints: rate limit by IP
- Auth endpoints (login, register, password reset): aggressive limits (5 req/min)
- Authenticated endpoints: rate limit by user ID

## Integration with DeepLocal Forge

Before implementing any endpoint that touches auth, user data, or external input:

```
/read skills/quality/security-best-practices.md
/architect
Review the following endpoint design for security issues:
[endpoint description or code]

Check:
1. Input validation completeness
2. Authorization (ownership check, not just authentication)
3. What data appears in logs
4. SQL injection surface
5. Any secrets exposed in response

Standards: see ai-specs/specs/backend-standards.mdc
```
