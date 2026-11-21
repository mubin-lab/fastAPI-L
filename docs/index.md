# Documentation index

A learning project: a layered, async FastAPI service with JWT auth (access + rotating refresh tokens), users/roles, projects and tasks.

| Doc | Read it to learn... |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | The layers, request lifecycle, folder tree, DI wiring, unit of work, error handling, trade-offs |
| [AUTH.md](AUTH.md) | Password hashing, token types and claims, login/refresh/logout flows, reuse detection, roles, limitations |
| [API.md](API.md) | Every endpoint with auth, request/response, errors and curl examples; pagination and error conventions |
| [DATABASE.md](DATABASE.md) | ER diagram, tables, indexes, sessions/transactions, Postgres swap, Alembic notes |
| [TESTING.md](TESTING.md) | Test strategy, fixtures, how to run and extend tests |
| [DEVELOPMENT.md](DEVELOPMENT.md) | Setup, env vars, "add a new resource" checklist, which agent/skill to use |

Suggested reading order for a newcomer: ARCHITECTURE -> API -> AUTH -> DATABASE -> TESTING -> DEVELOPMENT.

Interactive docs while the server runs: <http://localhost:8000/docs> (Swagger) and `/redoc`.
