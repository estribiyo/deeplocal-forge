# EXAMPLE-01: Item List Endpoint with Pagination
**Layer**: backend (Python/FastAPI)
**Status**: completed (reference example — do not modify)

> This file is a reference example showing the expected format for implementation plans.
> Create your own plans in this directory following this structure.

---

## Context

Add a paginated list endpoint to the Items API so the React frontend can display items
in pages of 20 without loading the full dataset.

**Ticket**: EXAMPLE-01
**User Story**: As a user, I want to browse items in pages so that the interface stays fast even with thousands of records.

---

## Architecture Impact

**Affected modules**
- `src/items/router.py` — add GET /items route
- `src/items/service.py` — add `list_items(page, limit)` method
- `src/items/repository.py` — add `find_paginated(offset, limit)` query
- `src/items/schemas.py` — add `ItemListResponse` schema

**New modules**: none

**Dependencies introduced**: none (pagination is built into SQLAlchemy)

---

## Implementation Steps

1. [ ] **Schema** — Add `ItemListResponse` to `schemas.py`
   - Fields: `data: list[ItemResponse]`, `meta: PaginationMeta`
   - `PaginationMeta`: `total: int`, `page: int`, `limit: int`
   - Success: `mypy` passes on the schema file

2. [ ] **Repository** — Add `find_paginated` to `ItemRepository`
   - Query: `SELECT * FROM items ORDER BY created_at DESC LIMIT $limit OFFSET $offset`
   - Also query total count: `SELECT COUNT(*) FROM items`
   - Use SQLAlchemy with parameterized query — no raw string interpolation
   - Success: returns `tuple[list[Item], int]`

3. [ ] **Service** — Add `list_items(page: int, limit: int) -> ItemListResponse`
   - Validate: `1 <= page`, `1 <= limit <= 100`
   - Calculate offset: `(page - 1) * limit`
   - Call repository, build response
   - Success: raises `ValueError` for invalid params; returns correct pagination meta

4. [ ] **Router** — Add `GET /items` route
   - Query params: `page: int = 1`, `limit: int = 20`
   - FastAPI dependency injection for DB session
   - Response model: `ItemListResponse`, status 200
   - Success: `curl localhost:8000/api/v1/items` returns paginated response

5. [ ] **Tests** — Write tests before implementation (TDD order)
   - See Test Specifications below

6. [ ] **API Spec** — Update `ai-specs/specs/api-spec.yml`
   - The `/items` GET path is already templated; fill in actual schemas

---

## Test Specifications

### Unit tests (`tests/items/test_service.py`)
- [ ] `test_list_items_returns_correct_page` — page 2, limit 5 returns items 6-10
- [ ] `test_list_items_returns_correct_total` — meta.total matches DB count
- [ ] `test_list_items_invalid_page_raises` — page=0 raises ValueError
- [ ] `test_list_items_limit_too_high_raises` — limit=101 raises ValueError
- [ ] `test_list_items_empty_collection` — returns empty data, total=0

### Integration tests (`tests/items/test_router.py`)
- [ ] `test_get_items_200` — GET /items returns 200 with valid structure
- [ ] `test_get_items_page_2` — page=2 returns different items than page=1
- [ ] `test_get_items_invalid_page_400` — GET /items?page=0 returns 400
- [ ] `test_get_items_limit_exceeds_max_400` — GET /items?limit=200 returns 400

---

## Error Handling

| Scenario            | HTTP status | Error code         |
|---------------------|-------------|---------------------|
| page < 1            | 400         | INVALID_PAGE        |
| limit < 1 or > 100  | 400         | INVALID_LIMIT       |
| DB connection error | 500         | INTERNAL_ERROR (log, do not expose) |

---

## Definition of Done

- [ ] All unit tests pass (`pytest tests/items/test_service.py`)
- [ ] All integration tests pass (`pytest tests/items/test_router.py`)
- [ ] Pre-LLM pipeline passes (`ruff format . && ruff check --fix . && mypy .`)
- [ ] Critic Pass completed — no issues found
- [ ] `ai-specs/specs/api-spec.yml` updated with actual schemas
- [ ] No `TODO` or `FIXME` left in changed files
- [ ] PR description references this plan
