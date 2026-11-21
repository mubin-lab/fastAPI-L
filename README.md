# FastAPI learning project

Layered async FastAPI service: JWT auth with rotating refresh tokens, users/roles, projects and tasks. SQLAlchemy 2.0 async + SQLite, Pydantic v2, managed with `uv`.

```bash
uv sync
cp .env.example .env            # set SECRET_KEY (>= 32 chars)
uv run uvicorn app.main:app --reload
uv run pytest -q
```

- Swagger UI: http://localhost:8000/docs
- API lives under `/api/v1` (auth, users, projects, tasks, health)
- Architecture: router -> service -> repository -> models

## Documentation
Start at [docs/index.md](docs/index.md): [ARCHITECTURE](docs/ARCHITECTURE.md) · [AUTH](docs/AUTH.md) · [API](docs/API.md) · [DATABASE](docs/DATABASE.md) · [TESTING](docs/TESTING.md) · [DEVELOPMENT](docs/DEVELOPMENT.md)

## Agents (`.claude/agents/`)
`architect` (design), `backend-engineer` (models, queries, auth), `fastapi-dev` (routers, schemas, tests). See DEVELOPMENT.md.

## Not implemented (by design)
Login rate limiting/lockout, Alembic migrations (tables via `create_all`), e-mail verification/password reset. See docs/AUTH.md and docs/DATABASE.md.
# fastAPI-L
