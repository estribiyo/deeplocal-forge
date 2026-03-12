# API Design Principles
Source: wshobson/agents · https://skills.sh/wshobson/agents/api-design-principles
License: MIT · https://github.com/wshobson/agents

## Overview

Good API design is about contracts, not implementation.
The API is a promise to its consumers — break it and you break their code.

## Core Principles

### 1. Design the contract before the code
Write the OpenAPI spec first. The spec is the source of truth, not the implementation.
Use `ai-specs/specs/api-spec.yml` as the starting point.

### 2. Resource-oriented design
- URLs identify resources, not actions: `/items` not `/getItems`
- HTTP verbs express the action: `GET /items` not `POST /items/list`
- Plural nouns for collections: `/users`, `/projects`, `/items`
- Nested only when truly hierarchical: `/projects/{id}/items`

### 3. Consistency over cleverness
- Same field names across all endpoints (`created_at`, not `createdAt` in some)
- Same error format everywhere (see backend-standards.mdc)
- Same pagination pattern everywhere (page + limit + total)

### 4. Be explicit about what changes
- Every field in a response is a commitment — removing it is a breaking change
- Use `nullable: true` explicitly — do not return absent fields sometimes
- Version (`/api/v1/`) before breaking anything

### 5. Fail clearly
```json
// Good — actionable error
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "fields": [
      { "field": "email", "message": "Invalid email format" }
    ]
  }
}

// Bad — useless to the caller
{ "error": "Bad request" }
```

## Design Checklist

Before writing implementation code:

- [ ] OpenAPI spec written for all new endpoints
- [ ] All success and error status codes documented
- [ ] Request and response schemas defined with examples
- [ ] Breaking changes identified (if any) and versioned
- [ ] Pagination strategy consistent with existing endpoints
- [ ] Auth requirements documented (`securitySchemes`)
- [ ] At least one colleague has read the spec (even if it's the LLM acting as reviewer)

## Integration with DeepLocal Forge

```
/architect
Think briefly (max 6 steps).
Design the API contract for: [endpoint description]

Output: OpenAPI 3.0 YAML snippet ready to paste into ai-specs/specs/api-spec.yml
Include: path, method, request schema, all response schemas, error cases.
Do not write implementation code.
Standards: see ai-specs/specs/backend-standards.mdc
```
