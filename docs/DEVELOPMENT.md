# Development guide

## Setup

```bash
uv sync                                   # install deps into .venv
cp .env.example .env                      # then set SECRET_KEY (>= 32 chars)
uv run uvicorn app.main:app --reload      # http://localhost:8000/docs
uv run pytest -q
```

Create the first admin: set `FIRST_ADMIN_EMAIL` and `FIRST_ADMIN_PASSWORD` in `.env` and start the app (created only if missing).

## Configuration (`app/core/config.py`)

| Variable | Default | Notes |
|---|---|---|
| `APP_NAME` | `Tasks API` | OpenAPI title |
| `ENVIRONMENT` | `development` | informational |
| `DEBUG` | `false` | log level / FastAPI debug |
| `DATABASE_URL` | `sqlite+aiosqlite:///./app.db` | async driver required |
| `SECRET_KEY` | dev placeholder | **>= 32 chars**, startup fails otherwise; always override outside dev |
| `ACCESS_TOKEN_MINUTES` | 15 | |
| `REFRESH_TOKEN_DAYS` | 7 | |
| `BCRYPT_ROUNDS` | 12 | 4-16 |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | JSON list; `*` rejected |
| `FIRST_ADMIN_EMAIL` / `FIRST_ADMIN_PASSWORD` | unset | optional admin bootstrap |

## Checklist: add a new resource (example: `Tag`)

1. **Model** `app/models/tag.py` (`Base`, `TimestampMixin`, FK + `index=True`); export in `app/models/__init__.py`.
2. **Schemas** `app/schemas/tag.py`: `TagCreate`, `TagUpdate` (optional fields; reject null for required ones), `TagRead` (`from_attributes=True`).
3. **Repository** `app/repositories/tag.py` extending `BaseRepository`; put every query here (scope by `owner_id`); export in `__init__.py`.
4. **Service** `app/services/tag_service.py`: business rules, raise `NotFound/Conflict/...` (never `HTTPException`). Use `exclude_unset=True` for PATCH.
5. **Dependencies** in `app/api/deps.py`: `get_tag_service` + `TagServiceDep` alias.
6. **Endpoints** `app/api/v1/endpoints/tags.py` with an `APIRouter(prefix="/tags", tags=["tags"])`; list endpoints return `Page[TagRead]` via `Pagination`.
7. **Register** the router in `app/api/v1/router.py`.
8. **Tests** `tests/test_tags.py`: happy path, 401, 404 isolation, 422, filters.
9. **Docs**: add the endpoints to `docs/API.md`, the table to `DATABASE.md`.
10. Schema change? `create_all` will create the new table on next start; for altered tables use Alembic (DATABASE.md).
11. Verify: `uv run pytest -q` and `uv run python -c "from app.main import app; print(list(app.openapi()['paths']))"`.

## Conventions

- Routers contain no business logic and no SQL.
- Services do not import FastAPI; repositories do not commit.
- Never lazy-load relationships in async code.
- Errors: raise a `DomainError` subclass; the envelope is produced centrally.
- Return other users' resources as 404.

## Agents and skills (`.claude/agents/`)

| Agent | Skill it reads | Use it for |
|---|---|---|
| `architect` | senior-architect | design decisions, trade-offs, Mermaid diagrams in docs/ |
| `backend-engineer` | senior-backend | models, repositories, queries/indexes, auth and API contract, security review |
| `fastapi-dev` | fastapi-developer | routers, schemas, dependencies, services, tests |

Example prompts: "use fastapi-dev to add a `Tag` resource following DEVELOPMENT.md"; "use backend-engineer to review the refresh-token flow".
