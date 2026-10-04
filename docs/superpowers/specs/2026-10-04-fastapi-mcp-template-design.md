# FastAPI and MCP Hello World Template Design

## Goal

Create a small, runnable Python template that demonstrates greeting REST endpoints in FastAPI, an HTTP MCP server, and PostgreSQL in Docker, with tests and MCP Inspector support. All application commands run in Docker; local source files are bind-mounted for development with automatic reload.

## User-visible behavior

- `GET /health` returns `{"status":"ok"}` and reports process health without depending on PostgreSQL.
- `POST /greetings` accepts `{"name":"Anar"}`, stores a greeting, and returns HTTP 201 with `id`, `name`, and `created_at`.
- `GET /greetings?limit=20` returns a JSON array of greetings, newest first. The accepted limit is 1 through 100.
- The MCP endpoint is served at `/mcp` over Streamable HTTP.
- MCP tool `create_greeting(name: str)` stores a greeting in PostgreSQL and returns its identifier, name, and creation time.
- MCP tool `list_greetings(limit: int = 20)` returns the newest stored greetings first. The accepted limit is 1 through 100.
- REST and MCP use the same greeting schema and database. MCP exposes structured results: a greeting object for creation and `{"greetings":[...]}` for listing, with a declared output schema.
- Names are trimmed before validation and storage. Empty or whitespace-only names are rejected; trimmed names are limited to 100 characters. Duplicate names are allowed.
- UUIDs are serialized as strings and creation timestamps as ISO 8601 UTC strings. Ordering is `created_at DESC, id DESC` to make timestamp ties deterministic.
- REST input errors return HTTP 422; database unavailability or a missing schema returns a sanitized HTTP 503. MCP failures use protocol-appropriate validation/tool errors and do not expose SQL, credentials, or connection strings.
- The database schema contains a `greetings` table with a UUID primary key, name, and timezone-aware creation timestamp.

## Architecture

One Python application container hosts FastAPI and the official MCP Python SDK v2 in one ASGI process. FastAPI serves health and greeting REST routes. The public MCP endpoint is exactly `/mcp`: mount the SDK ASGI app at `/` after the FastAPI routes, retaining its internal `/mcp` route. This avoids a doubled `/mcp/mcp` path and preserves the endpoint without a trailing-slash redirect. The parent application lifespan starts and stops the SDK session manager and disposes of the database engine. REST handlers and MCP tools share greeting schemas and a small application/data-access layer; neither issues SQL directly. Each operation owns its database session and transaction.

Docker Compose runs the application and PostgreSQL on a private project network. PostgreSQL has a readiness health check, and the application waits for that healthy state. The application does not silently create or migrate schema at startup: schema changes are applied by an explicit Alembic migration command.

The same PostgreSQL service hosts two distinct databases: the development database and a dedicated test database with its own login. Development credentials initialize PostgreSQL and are used only by the development app and one-shot provisioning service; the restricted test login owns the test database. The development app always uses the development database. Test containers and their migrations always use the test database. Tests must not truncate, drop, or migrate the development database. PostgreSQL data lives in a named volume; ordinary shutdown preserves it.

An optional Inspector Compose profile runs a pinned version of the official MCP Inspector web UI. Its backend connects to `http://app:<container-port>/mcp` over the Compose network; the browser opens the Inspector UI at its localhost URL. Host clients can separately reach MCP at `http://localhost:<app-port>/mcp`. The SDK transport-security allowlist explicitly accepts localhost and the Compose application hostname, with any required origins limited to the documented development URLs. Published application and Inspector ports bind to `127.0.0.1`; PostgreSQL needs no published host port.

Inspector's UI authentication stays enabled. Its generated token is supplied to the browser by the official UI rather than a printed token URL. Because the official Inspector prints its token in the startup banner, the Inspector service disables Docker log recording and runs detached; ordinary application log commands include only the app and PostgreSQL. Inspector receives no database credentials.

## Docker development workflow

- Bind-mount the project directory into the application, migration, and test containers at `/workspace`, so host edits to source, tests, and migrations are visible immediately.
- Keep installed dependencies and the container virtual environment outside `/workspace`, for example at `/opt/venv`. A host `.venv` must not replace or supply the container environment.
- Install the project in editable mode against `/workspace/src`, using the same source path at build time and runtime. Verify that the imported application module resolves inside the bind mount; reloading must not import a stale installed copy.
- Run the development application with Uvicorn automatic reload watching `src/`. Enable the reload watcher's polling through `etc/dev/.env` for reliable detection of bind-mounted edits. Updating application Python files takes effect without rebuilding the image.
- Run dependency installation, migrations, tests, and Inspector in Docker. The host only needs Docker with Compose and a shell for the `bin/` wrappers.
- Dependency or Dockerfile changes require rebuilding the image. Environment changes require recreating affected containers. Migration edits are visible immediately but schema changes still require an explicit migration command.
- First run: initialize both environment configurations and their separate secrets without overwriting existing files, build the image, start PostgreSQL and wait until healthy, run development migrations, then start the app. The README gives exact `bin/` commands for this sequence.
- `bin/test` starts the shared PostgreSQL service if needed, uses the one-shot provisioning service to create the test role/database if absent, then applies Alembic migrations with test credentials, and runs tests in a separate container using the same application factory/configuration model with `etc/test/.env`. The provisioning container receives development credentials through its process environment and the test credential file through a read-only Compose secret mount, so the two files can use the same variable names without one overwriting the other. Database setup and cleanup validate that the target is the configured test database and differs from the development database before changing data.
- Test runs execute serially initially and clean only their test database data. The template provides no reset command; ordinary up/down and test commands never remove the development volume.
- Database-failure tests create a separate application with an unreachable database address or a temporarily absent table in the test database. They do not stop the shared PostgreSQL service or change development configuration. All failure checks have bounded timeouts.
- A bootstrap image stage provides uv before `uv.lock` exists, so first dependency resolution and subsequent lock updates also run in Docker. Initialization copies each missing dev/test configuration from its example and each missing secret file from its environment's `secrets/.env.sample`, installs secret copies with mode `0600`, and never overwrites an existing file. Secret samples contain unusable placeholders; the developer replaces them with distinct environment-specific values before starting PostgreSQL.
- All wrappers resolve project and env-file paths relative to their own location, so they work when invoked from outside the project directory.
- The repository is a copy-and-rename starter. Before first initialization in a copied project, the developer can rename the package/project identifiers, Compose project and image names, database names, and the two sample login names. Provisioning validates configured identifiers but does not require a `template_` prefix or another template-specific namespace.

## Configuration and secrets

- Development configuration comes from `etc/dev/.env`; test configuration comes from `etc/test/.env`. Development PostgreSQL credentials come from `etc/dev/secrets/.env`; separate test credentials come from `etc/test/secrets/.env`. All application and Compose environment variables are sourced from these files.
- `etc/dev/.env` and `etc/test/.env` contain non-secret development and test settings and are checked in. Each has a matching `.env.example` for initialization.
- `etc/dev/secrets/.env` and `etc/test/secrets/.env` contain independent local database credentials and are git-ignored. Both use the same `POSTGRES_USER` and `POSTGRES_PASSWORD` variable names, but their values must differ. Their respective `.env.sample` files contain placeholders only.
- Both environment directories contain `.env.example` and `secrets/.env.sample` files documenting fresh-checkout values.
- The development file selects the development database; the test file selects the test database. Both identify the same Compose project and PostgreSQL service, with matching development/test database names for target guards. Reload is enabled only for the development application. Development and tests use distinct PostgreSQL logins and passwords. The test login owns only the test database; it cannot be a superuser, create databases or roles, replicate, bypass row-level security, inherit privileges, or participate in role memberships in either direction.
- `bin/compose` defaults to `--env-file etc/dev/.env`; `bin/compose --environment test` selects `etc/test/.env` for Compose interpolation. The app and PostgreSQL load development settings and `etc/dev/secrets/.env`; test containers load test settings and `etc/test/secrets/.env`. A separate one-shot provisioning service receives development credentials through its environment and reads the test credential file only from a read-only Compose secret at `/run/secrets/test-db.env`; this provisioning-only loader is the sole exception to the rule that ordinary application code reads configuration from process environment. The test runner receives only test credentials. `bin/test` validates shared database/project identity settings across both configurations before any database setup or cleanup, then selects the test configuration explicitly. Secrets never appear in command arguments, resolved diagnostic output, or logs; ordinary examples avoid inherited shell overrides.
- Secrets must not appear in Compose command-line arguments, checked-in examples, or logs.
- `.dockerignore` excludes both `etc/dev/secrets/` and `etc/test/secrets/`, local virtual environments, and generated caches from the image build context. The application/test/tooling project mounts mask `/workspace/etc` with an empty tmpfs so env files, including the other environment's secrets, are not exposed through mounted source; settings still arrive through Compose's process environment.

## Technology choices

- Python 3.12 or newer, constrained below Python 4.
- `uv` manages dependencies and a committed lockfile; complete image builds use `uv sync --locked` to reject a stale lockfile. The development image installs test dependencies as well as the editable application.
- FastAPI and Uvicorn provide the HTTP application runtime, with reload support for the development container.
- The official `mcp` Python package is constrained to `>=2,<3` and uses its v2 API and Streamable HTTP transport; its resolved version is recorded in `uv.lock`.
- SQLAlchemy 2 async APIs with `asyncpg` provide PostgreSQL access; Alembic manages schema migrations.
- `python-dotenv` is used only by the one-shot provisioning command to parse the read-only test credential mount; ordinary application and test settings continue to come only from process environment.
- Pytest, AnyIO's pytest plugin with the asyncio backend, HTTPX, and `asgi-lifespan` provide application and integration testing. HTTPX ASGI fixtures explicitly enter the parent lifespan; database engines, sessions, and MCP managers are created and disposed within the owning test event loop.
- Docker Compose defines the app, PostgreSQL, migration/test commands, and optional Inspector service. Python, PostgreSQL, uv, and Inspector images/tool versions are pinned rather than using floating `latest` tags.

## Tests and acceptance checks

- Unit tests run in Docker and cover greeting input validation and serialization without external services.
- PostgreSQL integration tests use only the dedicated test database on the shared Dockerized PostgreSQL service. They verify migration application, greeting persistence, deterministic ordering, and list limits; SQLite is not used as a substitute.
- REST tests verify creation/listing, HTTP status codes, shared validation, and persistence using an application configured for the test database.
- HTTP transport tests verify the exact `/mcp` URL, modern MCP discovery/tool calls, and a legacy initialization compatibility flow. They exercise the parent ASGI lifespan and the test database; in-memory tool calls alone do not satisfy transport coverage.
- Cross-interface tests create through REST and list through MCP, then create through MCP and list through REST, proving that both share the same operations and persistence.
- Error checks cover empty/oversized names, limit boundaries, database unavailability/missing schema, sanitized errors, and successful `GET /health` while the database is unavailable.
- Test-database target guards are verified, and running tests leaves existing development greetings intact.
- The documented manual Inspector flow opens the localhost UI, connects to `http://app:<container-port>/mcp`, creates a greeting, then lists it and confirms it persisted.
- A clean checkout can start with the documented `bin/` commands after initializing the development and test configurations and their separate secret env files; tests and migrations complete without a host Python installation or edits to application code.
- A manual development check edits a mounted application source file on the host and confirms that Uvicorn reloads and serves the change without rebuilding the image.
- Image verification checks editable import paths and confirms that changing `pyproject.toml` without updating `uv.lock` makes the complete image build fail.

## Project files

- `pyproject.toml` and `uv.lock`: package metadata, runtime/development dependencies, and reproducible resolution.
- `src/template_fastapi_mcp/main.py`: application factory, REST router inclusion, MCP mounting, and lifespan.
- `src/template_fastapi_mcp/api.py` and `schemas.py`: greeting REST routes and shared input/output schemas.
- `src/template_fastapi_mcp/config.py`: typed environment-backed settings.
- `src/template_fastapi_mcp/admin.py`: guarded test-role/database provisioning, provisioning-only secret-file loading, and explicit migration/test commands.
- `src/template_fastapi_mcp/db.py`: async engine and session lifecycle.
- `src/template_fastapi_mcp/models.py`: greeting persistence model.
- `src/template_fastapi_mcp/greetings.py`: greeting business/data-access operations.
- `src/template_fastapi_mcp/mcp_server.py`: MCP server and greeting tools.
- `alembic.ini` and `migrations/`: migration configuration and initial greetings-table revision.
- `tests/`: unit, HTTP, MCP, and PostgreSQL integration tests.
- `compose.yaml` and `Dockerfile`: app and database services, bind mounts/reload configuration, migration/test execution, and the optional Inspector profile.
- `etc/dev/.env`, `etc/dev/.env.example`, `etc/test/.env`, `etc/test/.env.example`, `etc/dev/secrets/.env.sample`, `etc/test/secrets/.env.sample`, `.gitignore`, and `.dockerignore`: separate environment defaults and independent secret-file handling.
- `bin/`: executable scripts for initial env setup, Compose up/down/logs, migration, tests, and Inspector.
- `README.md`: prerequisites, setup, common commands, endpoints/tools, and cleanup.

## Scope boundaries

This is a local development template, not a production deployment. Authentication, cloud deployment, TLS termination, connection pooling guidance, observability, and multi-user authorization are excluded. The database stores only greeting examples. Inspector is a development aid and is not exposed publicly.

## Implementation references

- [uv Docker integration](https://docs.astral.sh/uv/guides/integration/docker/): editable installs, external virtual environments, and locked builds.
- [FastAPI async tests](https://fastapi.tiangolo.com/advanced/async-tests/): async pytest execution and explicit lifespan management.
- [MCP SDK ASGI integration](https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/run/asgi.md): mounting and parent lifespan responsibilities.
- [MCP SDK deployment settings](https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/run/deploy.md): exact Host and Origin allowlists.
