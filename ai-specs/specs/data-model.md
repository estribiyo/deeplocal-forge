# Data Model & Domain

> Replace this template with the actual data model for your project.
> Keep this file in sync with the database schema — treat it as living documentation.

---

## Domain Entities

### [Entity Name]

| Field        | Type        | Constraints              | Description                        |
|--------------|-------------|--------------------------|------------------------------------|
| `id`         | UUID        | PK, NOT NULL             | Auto-generated primary key         |
| `name`       | VARCHAR(255)| NOT NULL                 | Display name                       |
| `description`| TEXT        | NULLABLE                 | Optional long-form description     |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW()  | Record creation timestamp (UTC)    |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW()  | Last modification timestamp (UTC)  |

**Indexes**
- Primary: `id`
- Query optimization: `created_at DESC` (for paginated list queries)

**Business Rules**
- `name` must be unique within a [parent entity / scope]
- Soft delete: records are not physically deleted; add `deleted_at TIMESTAMPTZ NULLABLE`

---

## Relationships

```
[Entity A] 1──── N [Entity B]
[Entity B] N──── N [Entity C]  (via join table entity_b_entity_c)
```

---

## Enumerations

### [EnumName]
| Value      | Description              |
|------------|--------------------------|
| `active`   | Record is in active use  |
| `archived` | Soft-deleted/hidden      |
| `draft`    | Not yet published        |

---

## Database Conventions

- All tables use snake_case
- Primary keys: UUID v4 (not auto-increment integers)
- Timestamps: always UTC, always `created_at` + `updated_at` on every table
- Boolean fields: prefix with `is_` or `has_` (`is_active`, `has_subscription`)
- Foreign keys: `<referenced_table_singular>_id` (e.g., `user_id`, `project_id`)
- Junction tables: `<table_a>_<table_b>` alphabetically sorted

---

## Migration History

| Version     | Description                          | Date       |
|-------------|--------------------------------------|------------|
| 001_initial | Initial schema                       | YYYY-MM-DD |
| 002_add_x   | Add [field] to [table]               | YYYY-MM-DD |

---

## Glossary

| Term       | Definition                                              |
|------------|---------------------------------------------------------|
| [Term]     | [Plain-language definition used in code and discussion] |
