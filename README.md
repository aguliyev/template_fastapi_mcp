# FastAPI + MCP Greeting Template

A Docker-only development template: greeting REST endpoints (FastAPI), an MCP
server (official `mcp` Python SDK v2, Streamable HTTP), and PostgreSQL, with an
isolated test database, MCP Inspector support, and automatic reload of mounted
source. All application commands run in Docker; the host only needs Docker with
Compose and a shell for the `bin/` wrappers.

## Prerequisites

- Docker Engine with the `docker compose` plugin and `compose up --wait`
  support (Compose 2.17 or newer). Verify with:

```bash
docker compose version
```

The wrappers deliberately do not fall back to legacy `docker-compose` v1.

## Copy and rename this template

This repository is a copy-and-rename starter. Before first initialization in a
copied project, rename these coordinated surfaces together:

- Repository directory.
- `[project].name` in `pyproject.toml`.
- Import package directory `src/template_fastapi_mcp/` and all imports of
  `template_fastapi_mcp`.
- Compose project name (`COMPOSE_PROJECT_NAME`) and image names in
  `compose.yaml`.
- Database names (`DEV_DB_NAME`, `TEST_DB_NAME`, `APP_DB_NAME`).
- Default sample login names in both `secrets/.env.sample` files.
- README title/examples and Python module references in Compose/Uvicorn
  commands.

Rename the checked-in examples and samples **before** `bin/init`. No
provisioning rule requires the original `template_fastapi_mcp` or `template_`
strings after those coordinated edits.

## First run

```bash
bin/init
# Edit etc/dev/secrets/.env and etc/test/secrets/.env, replacing every placeholder.
bin/check-secrets all
bin/build
bin/compose up -d --wait postgres
bin/migrate
bin/up
bin/test -q
bin/inspector
```

`bin/init` copies each missing `etc/dev/.env` / `etc/test/.env` from its
`.env.example`, and each missing `secrets/.env` from that environment's
`secrets/.env.sample` (mode `0600`), without overwriting existing values.
Both secret files use `POSTGRES_USER` and `POSTGRES_PASSWORD`, but you must
replace the placeholders with **different** development and test values before
running `bin/up`, `bin/migrate`, or `bin/test`. Changing development
credentials does not reinitialize a persisted PostgreSQL volume; guarded
provisioning updates only the configured test role's password without touching
development roles or data.

The committed `uv.lock` makes `bin/lock` unnecessary for ordinary checkout
setup; use it after dependency edits, then `bin/build` and recreate affected
containers.

## Commands

| Command | Purpose |
| --- | --- |
| `bin/init` | Copy missing configs/secrets, never overwrite |
| `bin/check-secrets {dev\|test\|all}` | Validate secret files without printing values |
| `bin/compose [--environment test] …` | Raw Compose access (dev config by default) |
| `bin/build` | Build the development image |
| `bin/lock` | Regenerate `uv.lock` in Docker |
| `bin/migrate` | Apply Alembic migrations to the dev database |
| `bin/up` | Start the app (waits until healthy) |
| `bin/down` | Stop services, preserving data |
| `bin/logs` | Follow `app` + `postgres` logs (Inspector excluded) |
| `bin/test …` | Provision test DB, migrate, run pytest |
| `bin/inspector` | Start the MCP Inspector web UI |

All wrappers resolve paths relative to their own location, so they work when
invoked from outside the project directory.

## Endpoints and tools

- `GET /health` → `{"status":"ok"}` (independent of PostgreSQL).
- `POST /greetings` accepts `{"name":"Anar"}`, returns HTTP 201:

```json
{"id":"…","name":"Anar","created_at":"2026-10-04T12:00:00Z"}
```

- `GET /greetings?limit=20` returns a JSON array, newest first
  (`created_at DESC, id DESC`). Limit: 1–100, default 20.
- Interactive docs: `/docs` and `/openapi.json`.
- MCP endpoint: `/mcp` over Streamable HTTP.
  - `create_greeting(name: str)` → greeting object (`id`, `name`, `created_at`).
  - `list_greetings(limit: int = 20)` → `{"greetings":[…]}`.
- Names are trimmed; empty/whitespace-only or >100 characters are rejected.
  Duplicate names are allowed. REST input errors are HTTP 422; storage failures
  are sanitized HTTP 503. MCP failures are protocol tool errors without SQL,
  credentials, or connection strings.

## Inspector

`bin/inspector` prints only the non-secret browser URL
(`http://localhost:6274` by default). In the UI, add a Streamable HTTP server
with the Compose-network target `http://app:8000/mcp`, connect, create `Anar`,
and list it. Host clients separately reach MCP at `http://localhost:8000/mcp`.
UI authentication stays enabled; the token is injected into the served page,
and Inspector logs are disabled so the token banner is not recorded.

## Development workflow

- Source hot reload: the project is bind-mounted at `/workspace` with
  dependencies at `/opt/venv` and the app installed editable against
  `/workspace/src`. Editing host Python files reloads via Uvicorn without a
  rebuild (polling enabled for bind mounts). Verify imports resolve under
  `/workspace/src/`.
- Dependency/Dockerfile changes: `bin/lock` (if `pyproject.toml` changed),
  then `bin/build` and recreate affected containers. A stale `uv.lock` fails
  the image build by design (`uv sync --locked`).
- Environment changes: recreate affected containers.
- Schema changes: edit migrations, then run the explicit `bin/migrate`
  (dev) — startup never migrates implicitly. Tests migrate the test database
  via `bin/test`.
- `bin/down` preserves the PostgreSQL volume; there is no automatic reset.

## Troubleshooting (sanitized)

- Unhealthy PostgreSQL: `bin/compose ps`, `bin/logs postgres`; confirm the dev
  secret file passes `bin/check-secrets dev` (mode `0600`, no placeholders).
- Missing migrations (`relation "greetings" does not exist`): run
  `bin/migrate` for dev, `bin/test` for the test database.
- MCP connection errors mentioning Host/Origin: use `http://app:8000/mcp`
  from inside Compose (Inspector) and `http://localhost:8000/mcp` from the
  host; check that requests carry an allowed Host.
- Stale lockfile build failure: run `bin/lock`, then `bin/build`.
- Missing/placeholder credentials: `bin/check-secrets all` fails without
  printing values; replace every placeholder with distinct dev/test values.
- Never print resolved Compose config or container environments containing
  credentials; use `bin/compose config --quiet` for validation.
