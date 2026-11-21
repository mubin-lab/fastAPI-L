# API reference

Base URL: `http://localhost:8000/api/v1`. Interactive version: `/docs`. All bodies are JSON except login (form).

## Conventions

**Auth**: `Authorization: Bearer <access_token>`. "Admin" = role `admin`.

**Error envelope** (every error, including 404 routes, 401 and 422):

```json
{"error": {"code": "not_found", "message": "Task not found", "details": null}}
```

422 `details` is a list: `[{"field": "body.title", "message": "String should have at least 1 character", "type": "string_too_short"}]`.

| Status | code | When |
|---|---|---|
| 400-ish domain | per error | rare |
| 401 | `unauthorized` | missing/invalid/expired token, wrong credentials |
| 403 | `forbidden` | not an admin, or account deactivated |
| 404 | `not_found` | missing OR not yours |
| 409 | `conflict` | duplicate e-mail, admin self-demotion |
| 422 | `validation_error` | bad body/query |
| 500 / 503 | `internal_error` / `service_unavailable` | server / DB problem |

**Pagination** (all list endpoints): `?page=1&size=20` (`page >= 1`, `1 <= size <= 100`). Response:

```json
{"items": [...], "total": 42, "page": 1, "size": 20, "pages": 3}
```

**Search** `q` is a case-insensitive substring match (wildcards are escaped).

Set once for the examples:
```bash
BASE=http://localhost:8000/api/v1
TOKEN=...   # access_token from login
```

## Health

| Endpoint | Auth | Response |
|---|---|---|
| `GET /health` | none | `200 {"status":"ok"}` liveness |
| `GET /health/ready` | none | `200 {"status":"ready","database":"ok"}`; `503` envelope if DB down |

Also available un-versioned at `/health` and `/health/ready` (hidden from Swagger).
`curl $BASE/health/ready`

## Auth

### POST /auth/register
Auth: none. Body `{"email", "password", "full_name"?}`. Password policy: >=10 chars, upper+lower+digit, <=72 bytes. Returns `201` user (`id, email, full_name, role, is_active, created_at`). Errors: 409 duplicate e-mail, 422 policy/e-mail.
```bash
curl -X POST $BASE/auth/register -H 'content-type: application/json' \
  -d '{"email":"me@example.com","password":"Str0ngPassw0rd!","full_name":"Me"}'
```

### POST /auth/login
Auth: none. **Form** body `username` (the e-mail) + `password`. Returns `200 {"access_token","refresh_token","token_type":"bearer","expires_in":900}`. Errors: 401 bad credentials, 403 deactivated.
```bash
curl -X POST $BASE/auth/login -d 'username=me@example.com&password=Str0ngPassw0rd!'
```

### POST /auth/refresh
Auth: none (the refresh token is the credential). Body `{"refresh_token"}`. Returns a new token pair; the old refresh token is revoked. Errors: 401 invalid/expired/wrong type/unknown, 401 on reuse (and all sessions revoked).
```bash
curl -X POST $BASE/auth/refresh -H 'content-type: application/json' -d '{"refresh_token":"<R>"}'
```

### POST /auth/logout
Auth: none. Body `{"refresh_token"}`. `204`. Revokes that refresh token. 401 if the token is malformed or not a refresh token.

### POST /auth/logout-all
Auth: user. `204`. Revokes every refresh token of the caller.
`curl -X POST $BASE/auth/logout-all -H "Authorization: Bearer $TOKEN"`

### POST /auth/change-password
Auth: user. Body `{"current_password","new_password"}`. `204`; revokes all refresh tokens. 401 wrong current password, 422 weak new password.

### GET /auth/me
Auth: user. `200` current user.

## Users

### GET /users/me, PATCH /users/me
Auth: user. PATCH body `{"full_name"?}` (role/e-mail cannot be changed here; unknown fields are ignored). `200` user.
```bash
curl -X PATCH $BASE/users/me -H "Authorization: Bearer $TOKEN" -H 'content-type: application/json' -d '{"full_name":"New Name"}'
```

### GET /users  (admin)
Query: `page,size,q` (e-mail/name), `role` (`user|admin`), `is_active`. `200` Page of users. Errors: 401, 403.
`curl "$BASE/users?q=alice&role=user" -H "Authorization: Bearer $ADMIN"`

### GET /users/{user_id}  (admin)
`200` user, 404 if missing.

### PATCH /users/{user_id}  (admin)
Body `{"role"?: "user|admin", "is_active"?: bool}`. `200` user. 409 if the admin targets themselves with a demotion/deactivation; deactivating revokes the user's refresh tokens.

### DELETE /users/{user_id}  (admin)
Deactivates (soft delete, no row removed). `204`. 409 for self, 404 missing.

## Projects

Fields: `id, owner_id, name, description, archived, created_at, updated_at`. Users see only their projects; admins see all (read-only). Writes on someone else's project: 404.

| Endpoint | Body / query | Response |
|---|---|---|
| `POST /projects` | `{"name"(1-120), "description"?}` | `201` project |
| `GET /projects` | `page,size,q,archived` | `200` Page |
| `GET /projects/{id}` | | `200` / 404 |
| `PATCH /projects/{id}` | any of `name, description, archived` (only sent fields change; `name`/`archived` cannot be null) | `200` / 404 / 422 |
| `DELETE /projects/{id}` | | `204` (also deletes its tasks) / 404 |

```bash
curl -X POST $BASE/projects -H "Authorization: Bearer $TOKEN" -H 'content-type: application/json' \
  -d '{"name":"Website","description":"Redesign"}'
```

## Tasks

Fields: `id, project_id, owner_id, title, description, status (todo|in_progress|done), priority (low|medium|high), due_date (YYYY-MM-DD|null), created_at, updated_at`.

| Endpoint | Body / query | Response |
|---|---|---|
| `POST /tasks` | `{"project_id", "title"(1-200), "description"?, "status"?=todo, "priority"?=medium, "due_date"?}` | `201`; 404 if the project is not yours |
| `GET /tasks` | filters below | `200` Page |
| `GET /tasks/{id}` | | `200` / 404 |
| `PATCH /tasks/{id}` | any of `title, description, status, priority, due_date` (`due_date`/`description` may be set to null to clear; `title/status/priority` may not) | `200` / 404 / 422 |
| `DELETE /tasks/{id}` | | `204` / 404 |

List filters: `project_id`, `status`, `priority`, `due_before` (date, strictly before; tasks with no due date are excluded), `q` (title/description), `sort_by` (`created_at|due_date|priority|title|status`, default `created_at`), `order` (`asc|desc`, default `desc`), `page`, `size`. Priority sorts by rank (low < medium < high), not alphabetically.

```bash
curl "$BASE/tasks?status=todo&priority=high&due_before=2030-12-31&sort_by=due_date&order=asc&size=10" \
  -H "Authorization: Bearer $TOKEN"
curl -X PATCH $BASE/tasks/1 -H "Authorization: Bearer $TOKEN" -H 'content-type: application/json' -d '{"status":"done"}'
```

The old un-versioned `/auth/*` and `/tasks` paths no longer exist (404 envelope).
