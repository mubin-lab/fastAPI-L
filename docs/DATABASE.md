# Database

SQLAlchemy 2.0 async ORM. Default: SQLite file `app.db` through `aiosqlite` (`DATABASE_URL`). Models live in `app/models/`, base in `app/db/base.py`, engine/session in `app/db/session.py`.

## ER diagram

```mermaid
erDiagram
    users ||--o{ refresh_tokens : "has"
    users ||--o{ projects : "owns"
    users ||--o{ tasks : "owns"
    projects ||--o{ tasks : "contains"
    users {
        int id PK
        string email UK
        string full_name
        string hashed_password
        string role "user|admin"
        bool is_active
        datetime created_at
        datetime updated_at
    }
    refresh_tokens {
        int id PK
        int user_id FK
        string token_hash UK "sha256 hex"
        datetime expires_at
        datetime revoked_at "null = active"
        datetime created_at
    }
    projects {
        int id PK
        int owner_id FK
        string name
        text description
        bool archived
        datetime created_at
        datetime updated_at
    }
    tasks {
        int id PK
        int project_id FK
        int owner_id FK
        string title
        text description
        string status "todo|in_progress|done"
        string priority "low|medium|high"
        date due_date
        datetime created_at
        datetime updated_at
    }
```

## Indexes (why each exists)

| Table | Index | Serves |
|---|---|---|
| users | `email` unique | login lookup, duplicate check |
| users | `role`, `is_active` | admin list filters |
| refresh_tokens | `user_id` | revoke-all for a user |
| refresh_tokens | `token_hash` unique | refresh/logout lookup |
| projects | `owner_id`; `(owner_id, archived)`; `name` | ownership scope, archived filter, name search/sort |
| tasks | `project_id`, `owner_id` | FK lookups and ownership scope |
| tasks | `status`, `priority`, `due_date`; `(owner_id, status)` | filters and sorting |

Note: `ILIKE '%text%'` searches cannot use a normal B-tree index. For large data use Postgres `pg_trgm` or full-text search.

## Foreign keys and deletes

FKs use `ON DELETE CASCADE`. SQLite ignores FKs by default, so `make_engine` enables `PRAGMA foreign_keys=ON` on each connection. Deleting a project also explicitly deletes its tasks in `ProjectRepository.delete_with_tasks` (works even if cascades were off). Users are never hard-deleted by the API (only deactivated).

## Relationships and lazy loading

There are intentionally **no `relationship()`s**. Async SQLAlchemy cannot lazy-load (it raises `MissingGreenlet`), so we query by FK columns instead. If you add one, declare `lazy="raise"` and load explicitly:

```python
select(Project).options(selectinload(Project.tasks))
```

## Sessions and transactions

- `SessionFactory = async_sessionmaker(engine, expire_on_commit=False)`: objects stay readable after commit (needed because responses are serialized after the commit).
- `get_db` yields one session per request; commit on success, rollback on exception (see ARCHITECTURE.md section 5).
- Repositories `flush()` + `refresh()` so server defaults (`created_at`) and IDs are available immediately.
- Timestamps use `server_default=func.now()`; SQLite returns naive datetimes, so security code uses `ensure_utc()` when comparing.

## Creating tables

`lifespan` runs `Base.metadata.create_all` at startup. This only creates **missing tables**; it never alters existing ones. After changing a model, delete `app.db` (dev only) or adopt Alembic.

## Swapping to Postgres

1. `uv add asyncpg`
2. `DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/appdb`
3. Replace `create_all` with Alembic migrations.
4. Consider: `sqlalchemy.Enum`/native enums or CHECK constraints for status/priority/role, `TIMESTAMPTZ` (already `timezone=True`), `SELECT ... FOR UPDATE` in refresh rotation, connection pool settings (`pool_size`, `pool_pre_ping=True`).
5. The SQLite-only PRAGMA listener is skipped automatically (it checks the URL).

## Alembic notes (not installed yet)

```bash
uv add alembic
uv run alembic init -t async migrations
# migrations/env.py: import app.models; target_metadata = Base.metadata; set sqlalchemy.url from settings
uv run alembic revision --autogenerate -m "initial"
uv run alembic upgrade head
```
Then remove `create_all` from `lifespan`. For SQLite use `render_as_batch=True` in `env.py` because it cannot ALTER most things.
