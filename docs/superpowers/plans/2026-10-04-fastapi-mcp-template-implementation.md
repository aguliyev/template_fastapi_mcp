# FastAPI and MCP Template Implementation Plan

> **For agentic workers:** Use `superpowers:executing-plans` to implement this plan task by task in the current session. Steps use checkbox syntax. Subagent-driven development is an alternative only when delegation is authorized. This document plans future work; unchecked commands and tests have not been executed.

**Goal:** Build a Docker-only development template with greeting REST endpoints, MCP tools, PostgreSQL, an isolated test database, Inspector, and automatic reload of mounted local source.

**Architecture:** One application factory composes FastAPI and the official MCP SDK's ASGI application. Both interfaces call the same greeting service, which owns short SQLAlchemy async transactions. Compose hosts one PostgreSQL instance containing separate development and test databases; tests run their own application instances.

**Tech Stack:** Python 3.12+, uv, FastAPI, Uvicorn, official `mcp>=2,<3`, SQLAlchemy 2, asyncpg, Alembic, pytest, AnyIO/asyncio, HTTPX, asgi-lifespan, Docker Compose, MCP Inspector.

**Spec:** `../specs/2026-10-04-fastapi-mcp-template-design.md`.

## Global constraints

- Python 3.12 or newer, constrained below Python 4.
- The official `mcp` Python package is constrained to `>=2,<3`.
- All application commands run in Docker. Do not install dependencies or execute Python/pytest/uv on the host.
- Development configuration comes from `etc/dev/.env`; test configuration comes from `etc/test/.env`. Development credentials come from `etc/dev/secrets/.env`; test credentials come from `etc/test/secrets/.env`. Both secret files use `POSTGRES_USER` and `POSTGRES_PASSWORD`, with distinct values. Test credentials do not grant PostgreSQL admin privileges. Ordinary application code reads only process environment variables; the provisioning command alone reads the test credential file from a read-only Compose secret because both environments intentionally use the same keys.
- The development database and test database share a PostgreSQL service but have distinct names. Tests must not truncate, drop, or migrate the development database.
- Bind-mount the project at `/workspace`; install dependencies at `/opt/venv` and the application in editable mode against `/workspace/src`.
- Complete image builds use `uv sync --locked`. Commit the generated `uv.lock`.
- Schema migrations are explicit commands. No schema creation or migration in application startup.
- Publish application and Inspector ports on `127.0.0.1` only. Do not publish PostgreSQL.
- Unit tests require no running database. Integration tests use PostgreSQL, not SQLite.
- Names are trimmed, nonempty, at most 100 characters, and may repeat. List limits are 1 through 100, default 20.
- Order greetings by `created_at DESC, id DESC`; serialize UUID strings and ISO 8601 UTC timestamps.
- REST validation errors are 422; storage failures are sanitized 503 responses. MCP exposes sanitized tool errors.
- Ordinary shutdown preserves the PostgreSQL volume. No automatic destructive reset.
- Work only under `projects/template_fastapi_mcp`; preserve existing repository changes and the human-only scratchpad.

## Execution conventions and file ownership

Run shell commands from `/home/anar/git/aguliyev/jobsearch/projects/template_fastapi_mcp` unless a step names another directory. All paths below are relative to that project. `bin/compose` is the common wrapper; the `bin/test` command prepares and migrates only the test database. Before Task 3 provides that command, use the indicated direct Docker test commands.

Each task ends with a verification checkpoint. Commit only that task's named files after verification; do not stage the entire repository. The planning handoff does not itself create commits or application files.

| Files | Responsibility | Task |
| --- | --- | --- |
| `pyproject.toml`, `uv.lock`, `Dockerfile`, `compose.yaml` | Dependency bootstrap, editable runtime, services | 1 |
| `etc/dev/.env`, `etc/dev/.env.example`, `etc/test/.env`, `etc/test/.env.example`, `etc/dev/secrets/.env.sample`, `etc/test/secrets/.env.sample`, `.gitignore`, `.dockerignore` | Separate configurations and credentials, image exclusions | 1 |
| `bin/init`, `bin/check-secrets`, `bin/compose`, `bin/build`, `bin/lock` | Reproducible Docker setup | 1 |
| `src/template_fastapi_mcp/__init__.py`, `config.py`, `schemas.py` | Package, settings, shared contracts | 1–2 |
| `db.py`, `models.py`, `admin.py`, `alembic.ini`, `migrations/env.py`, `migrations/script.py.mako`, `migrations/versions/0001_greetings.py`, `tests/unit/test_admin_guards.py` | Database lifecycle, guarded provisioning, migrations | 3 |
| `greetings.py` | Shared persistence operations and sanitized errors | 4 |
| `api.py`, `main.py` | REST and application lifespan | 5 |
| `mcp_server.py` | Tool registration and transport integration | 6 |
| `tests/conftest.py`, `tests/unit/`, `tests/integration/` | Async fixtures, isolated database and live HTTP checks | 2–7 |
| `bin/up`, `bin/down`, `bin/logs`, `bin/migrate`, `bin/test`, `bin/inspector`, `README.md` | Developer commands and acceptance flow | 3, 5, 8 |

## Task 1: Docker dependency bootstrap and mounted development image

**Files:** Create package metadata, `__init__.py`, Docker/Compose files, env examples/defaults, ignore files, and `bin/init`, `bin/check-secrets`, `bin/compose`, `bin/build`, `bin/lock`.

**Interfaces:** Produces a bootstrap service named `tooling`, a development image shared by `app` and `tests`, PostgreSQL service `postgres`, and wrappers accepting arbitrary arguments without changing their quoting.

- [ ] **Step 1: Establish the first smoke-check failure.**

```bash
bin/compose --profile tools run --rm --no-deps tooling uv --version
```

Expected before implementation: missing wrapper/service. This setup task uses command smoke checks rather than tests duplicating YAML.

- [ ] **Step 2: Define metadata and configuration.**

Use Hatchling with packages rooted at `src/template_fastapi_mcp`; create an empty `__init__.py`. Include this metadata:

```toml
[project]
name = "template-fastapi-mcp"
version = "0.1.0"
requires-python = ">=3.12,<4"
dependencies = [
  "fastapi>=0.115,<1", "uvicorn[standard]>=0.30,<1", "mcp>=2,<3",
  "sqlalchemy>=2,<3", "asyncpg>=0.30,<1", "alembic>=1.13,<2",
  "pydantic>=2,<3", "pydantic-settings>=2,<3", "python-dotenv>=1,<2",
]

[dependency-groups]
dev = ["pytest>=8,<10", "anyio>=4,<5", "httpx>=0.28,<1", "asgi-lifespan>=2,<3"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/template_fastapi_mcp"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-p no:cacheprovider"
markers = ["integration: requires the isolated PostgreSQL test database"]
```

Make `etc/dev/.env` and `etc/dev/.env.example` identical initially:

```dotenv
COMPOSE_PROJECT_NAME=template_fastapi_mcp
PYTHON_IMAGE=python:3.12.15-slim-bookworm
UV_IMAGE=ghcr.io/astral-sh/uv:0.12.23
POSTGRES_IMAGE=postgres:17.11-bookworm
INSPECTOR_IMAGE=ghcr.io/modelcontextprotocol/inspector:2.9.0
DEV_DB_NAME=template_fastapi_mcp
TEST_DB_NAME=template_fastapi_mcp_test
APP_DB_NAME=template_fastapi_mcp
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
APP_PORT=8000
UVICORN_HOST=0.0.0.0
UVICORN_PORT=8000
TEST_HTTP_PORT=18000
CLIENT_PORT=6274
HOST=0.0.0.0
DANGEROUSLY_BIND_ALL_INTERFACES=true
MCP_AUTO_OPEN_ENABLED=false
UV_PROJECT_ENVIRONMENT=/opt/venv
UV_CACHE_DIR=/tmp/uv-cache
UV_LINK_MODE=copy
PYTHONDONTWRITEBYTECODE=1
WATCHFILES_FORCE_POLLING=true
```

Create `etc/test/.env` and `etc/test/.env.example` from the same complete non-secret defaults, changing `APP_DB_NAME` to `template_fastapi_mcp_test` and `WATCHFILES_FORCE_POLLING` to `false`. Test servers run without `--reload`. The Compose project name, database host/port, and both database names must match the development file so both configurations share one PostgreSQL service.

Create these independently editable samples:

```dotenv
# etc/dev/secrets/.env.sample
POSTGRES_USER=replace_me_dev
POSTGRES_PASSWORD=replace-me
```

```dotenv
# etc/test/secrets/.env.sample
POSTGRES_USER=replace_me_test
POSTGRES_PASSWORD=replace-me
```

Both environments deliberately use the same keys; their values must differ. `bin/init` copies each dev/test configuration example only when its corresponding `.env` is absent and installs each missing `secrets/.env` from that environment's `.env.sample` with mode `0600`. Use a same-directory mode-0600 temporary file, copy the sample into it, create the destination with an atomic no-overwrite hard link, and clean up via a trap. Never overwrite an existing file or print its contents. The copied placeholders are not usable credentials: after copying or renaming the template, the developer edits both ignored secret files before starting PostgreSQL.

`bin/check-secrets dev`, `bin/check-secrets test`, and `bin/check-secrets all` validate without printing values. For each requested file, require exactly one nonempty `POSTGRES_USER` and `POSTGRES_PASSWORD`, reject `replace_me_dev`, `replace_me_test`, and `replace-me`, and require mode `0600` where the host supports POSIX modes. The `all` form also requires development and test usernames and passwords to differ. Limit secret files to unquoted, single-line `KEY=value` entries so the checker can read the substring after the first `=` without sourcing either file. `bin/migrate`, `bin/up`, and `bin/test` call the relevant checker before starting PostgreSQL.

- [ ] **Step 3: Implement the bootstrap stage and external virtual environment.**

```dockerfile
ARG PYTHON_IMAGE
ARG UV_IMAGE
FROM ${UV_IMAGE} AS uv_binary
FROM ${PYTHON_IMAGE} AS bootstrap
COPY --from=uv_binary /uv /usr/local/bin/uv
WORKDIR /workspace

FROM bootstrap AS development
ARG UV_PROJECT_ENVIRONMENT
ENV UV_PROJECT_ENVIRONMENT=${UV_PROJECT_ENVIRONMENT}
ENV PATH="${UV_PROJECT_ENVIRONMENT}/bin:${PATH}"
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --group dev --no-install-project
COPY src ./src
RUN uv sync --locked --group dev
```

Keep the application editable. Never add `--no-editable` to this development image. Use `/workspace` in both stages so the editable import path survives the bind mount. Bootstrap can be built before `uv.lock` exists; development cannot.

Use this service structure before adding the app command in Task 5:

```yaml
x-development: &development
  image: template_fastapi_mcp:dev
  build:
    context: .
    target: development
    args:
      PYTHON_IMAGE: ${PYTHON_IMAGE}
      UV_IMAGE: ${UV_IMAGE}
      UV_PROJECT_ENVIRONMENT: ${UV_PROJECT_ENVIRONMENT}
  working_dir: /workspace
  env_file: [etc/dev/.env, etc/dev/secrets/.env]
  volumes: [".:/workspace"]
  tmpfs: [/workspace/etc]

services:
  tooling:
    profiles: [tools]
    image: template_fastapi_mcp-tooling:dev
    build:
      context: .
      target: bootstrap
      args:
        PYTHON_IMAGE: ${PYTHON_IMAGE}
        UV_IMAGE: ${UV_IMAGE}
    working_dir: /workspace
    env_file: [etc/dev/.env]
    volumes: [".:/workspace"]
    tmpfs: [/workspace/etc]
  postgres:
    image: ${POSTGRES_IMAGE}
    env_file: [etc/dev/.env, etc/dev/secrets/.env]
    environment:
      POSTGRES_DB: ${DEV_DB_NAME}
    volumes: ["postgres_data:/var/lib/postgresql/data"]
    healthcheck:
      test: [CMD-SHELL, 'pg_isready -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"']
      interval: 2s
      timeout: 3s
      retries: 30
  app:
    <<: *development
    ports: ["127.0.0.1:${APP_PORT}:${UVICORN_PORT}"]
    depends_on:
      postgres:
        condition: service_healthy
  provision:
    <<: *development
    profiles: [test]
    env_file: [etc/dev/.env, etc/dev/secrets/.env]
    secrets:
      - source: test_db_credentials
        target: test-db.env
    depends_on:
      postgres:
        condition: service_healthy
  tests:
    <<: *development
    profiles: [test]
    env_file: [etc/test/.env, etc/test/secrets/.env]
    depends_on:
      postgres:
        condition: service_healthy

volumes:
  postgres_data:

secrets:
  test_db_credentials:
    file: ./etc/test/secrets/.env
```

The Compose default network provides service-name resolution. Test, provisioning, and tooling containers publish no ports. `.dockerignore` excludes both `etc/dev/secrets/` and `etc/test/secrets/`, `.venv/`, `.git/`, `__pycache__/`, `.pytest_cache/`, and build artifacts; ignore both copied secret files and local Python artifacts in `.gitignore`. Track both `.env.sample` files explicitly. The tmpfs overlay hides mounted environment files from app, tests, provision, and tooling; Compose injects ordinary settings independently. Only the provisioning service can read `/run/secrets/test-db.env`, and it receives development credentials—not test credentials—through its process environment.

- [ ] **Step 4: Add cwd-independent wrappers and create the lockfile in Docker.**

The common wrapper resolves its own location and uses absolute paths:

```bash
#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
environment_name=dev
if [[ "${1:-}" == "--environment" ]]; then
  environment_name="${2:?Missing environment name}"
  shift 2
fi
case "$environment_name" in
  dev|test) ;;
  *) printf '%s\n' "Environment must be dev or test" >&2; exit 2 ;;
esac
exec docker compose --project-directory "$project_root" \
  --env-file "$project_root/etc/$environment_name/.env" -f "$project_root/compose.yaml" "$@"
```

`bin/compose` defaults to development interpolation; `bin/compose --environment test` selects the test config. Service `env_file` paths remain explicit: app/PostgreSQL load development settings, tests load test settings, and both use the same credential key names from their own secret files. Both configs retain the same Compose project name. The one-shot provisioning service gets development credentials from its environment and the test file from the read-only secret mount; tests receive only test credentials. `bin/build` runs `bin/compose build app`. `bin/lock` builds `tooling`, then runs `uv lock` through that service as the host UID/GID, preserving ownership of the mounted lockfile. Its command is:

```bash
bin/compose --profile tools build tooling
bin/compose --profile tools run --rm --no-deps \
  --user "$(id -u):$(id -g)" tooling uv lock
```

Every wrapper uses its resolved script directory to call `bin/compose`, not a relative path from the caller. Make the scripts executable.

At the start of `bin/init`, require `docker compose version` to succeed and feature-detect `--wait` with `docker compose up --help` without printing environment or secret data. Fail with a fixed prerequisite message when the Compose plugin is absent or too old. Do not support the legacy `docker-compose` v1 command.

- [ ] **Step 5: Verify setup and checkpoint.**

```bash
bin/init
# Replace the placeholders in both ignored secrets/.env files before continuing.
bin/check-secrets all
bin/lock
bin/build
bin/compose --profile test run --rm --no-deps tests \
  python -c 'import template_fastapi_mcp; print(template_fastapi_mcp.__file__)'
```

Expected: `bin/init` copies missing files and reports that placeholder credentials must be replaced; `bin/check-secrets all` fails until both ignored copies contain distinct non-placeholder credentials, then succeeds silently. Pinned tooling runs, the lockfile is generated without host Python, the image builds successfully, and the import path starts with `/workspace/src/`. Run `bin/init` a second time and verify both configuration and secret-file bytes are unchanged without printing secrets. Confirm `git check-ignore etc/dev/secrets/.env etc/test/secrets/.env` succeeds and neither `.env.sample` is ignored. Verify the test container has `POSTGRES_USER` and `POSTGRES_PASSWORD` without printing either, and verify its username differs from the development username using the silent checker rather than container output. Require both mounted source secret paths under `/workspace/etc` to be absent because of the tmpfs overlay. Check Compose with `config --quiet`, never log a fully resolved config containing credentials. Checkpoint only Task 1 files.

## Task 2: Shared validation, typed settings, and async unit tests

**Files:** Create `config.py`, `schemas.py`, `tests/conftest.py`, `tests/unit/test_schemas.py`, and `tests/unit/test_config.py`.

**Interfaces:** Produces `Settings`, `Settings.database_url -> sqlalchemy.engine.URL`, `Settings.assert_test_target() -> None`, `GreetingCreate`, `GreetingOut`, `GreetingList`, `Name`, and `Limit`.

- [ ] **Step 1: Write validation tests before their modules.**

```python
import pytest
from pydantic import ValidationError
from template_fastapi_mcp.schemas import GreetingCreate

def test_name_is_trimmed():
    assert GreetingCreate(name="  Anar\t").name == "Anar"

@pytest.mark.parametrize("name", ["", " \t\n", "a" * 101, None, 123])
def test_invalid_names(name):
    with pytest.raises(ValidationError):
        GreetingCreate(name=name)

def test_trimmed_length_boundary():
    assert len(GreetingCreate(name=" " + "a" * 100 + " ").name) == 100
```

Run `bin/compose --profile test run --rm --no-deps tests pytest tests/unit -q`. Expected initially: missing-module collection failure; after modules exist, behavioral failures must precede their fixes.

- [ ] **Step 2: Implement the shared schemas.**

```python
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints, field_serializer

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Limit = Annotated[int, Field(ge=1, le=100)]

class GreetingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Name

class GreetingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    created_at: AwareDatetime

    @field_serializer("created_at", when_used="json")
    def utc_timestamp(self, value: datetime) -> str:
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")

class GreetingList(BaseModel):
    greetings: list[GreetingOut]
```

Add these named tests in `tests/unit/test_schemas.py`: `test_greeting_out_serializes_uuid_and_converts_aware_timestamp_to_utc`, `test_greeting_out_rejects_naive_timestamp`, and `test_limit_boundaries`. Use UUID `00000000-0000-0000-0000-000000000001` and `2026-10-04T07:00:00-05:00`; require `model_dump(mode="json")` to contain the UUID string and `2026-10-04T12:00:00Z`. In the boundary test, use `TypeAdapter(Limit)`, accept 1 and 100, and require `ValidationError` for 0 and 101.

- [ ] **Step 3: Implement explicit environment-backed settings and test-target guards.**

Use `BaseSettings` with `SettingsConfigDict(env_file=None, extra="ignore", populate_by_name=True, hide_input_in_errors=True)`; fields are `postgres_host: str`, `postgres_port: int`, `postgres_user: str`, `postgres_password: SecretStr`, `dev_db_name: str`, `test_db_name: str`, `app_db_name: str`, `app_port: int`, `uvicorn_port: int`, `test_http_port: int`, and `client_port: int`. Every field reads its matching uppercase environment variable, including `POSTGRES_USER` and `POSTGRES_PASSWORD`. Development and test containers use identical key names but load different files, so no alias fallback or mixed-credential validator is needed. Explicit constructor values by field name retain priority over environment sources; Task 3 uses that supported path to construct validated test settings from the mounted test credential file. Build the URL without string concatenation:

```python
@property
def database_url(self) -> URL:
    return URL.create(
        "postgresql+asyncpg", username=self.postgres_user,
        password=self.postgres_password.get_secret_value(),
        host=self.postgres_host, port=self.postgres_port, database=self.app_db_name,
    )

def assert_test_target(self) -> None:
    if self.app_db_name != self.test_db_name or self.test_db_name == self.dev_db_name:
        raise ValueError("Refusing a database operation outside the test database")
```

Validate all database names and the selected login name against `[a-z][a-z0-9_]{0,62}` using field validation. Add named tests `test_database_url_escapes_reserved_password_characters`, `test_settings_require_both_credentials`, `test_test_target_rejects_equal_database_names`, `test_test_target_rejects_development_database`, and `test_settings_repr_and_url_mask_password`. Use a password containing `@`, `:`, and `%`; confirm `repr(settings)` and default URL rendering mask credentials. Do not dump a full settings validation error containing input secrets to logs.

- [ ] **Step 4: Fix the async runner and verify the unit checkpoint.**

`tests/conftest.py` initially contains only:

```python
import pytest

@pytest.fixture
def anyio_backend():
    return "asyncio"
```

Run the same Docker unit command. Expected: all unit tests pass with PostgreSQL stopped or absent. Imports must not construct a global database engine. Checkpoint Task 2 files.

## Task 3: PostgreSQL migration and guarded test-database provisioning

**Files:** Create `db.py`, `models.py`, `admin.py`, Alembic files, `bin/migrate`, `bin/test`, `tests/unit/test_admin_guards.py`, and `tests/integration/test_database.py`; extend `tests/conftest.py`.

**Interfaces:** Produces `Database(settings)` exposing `engine`, `sessions: async_sessionmaker[AsyncSession]`, and `async close() -> None`; `Greeting` and `Base`; `load_test_settings(base_settings: Settings, secret_path: Path) -> Settings`; `ensure_test_database(settings: Settings, *, admin_user: str, admin_password: SecretStr) -> None`; CLI `python -m template_fastapi_mcp.admin migrate`, `provision-test`, and `test [pytest arguments]`. Also export synchronous `run_migrations(settings: Settings) -> None`, `run_tests(settings: Settings, pytest_args: list[str]) -> int`, and `main(argv: list[str] | None = None) -> int`.

- [ ] **Step 1: Specify the first database integration check.**

```python
import pytest
from sqlalchemy import text

@pytest.mark.anyio
@pytest.mark.integration
async def test_migrated_database_is_test_database(db, test_settings):
    async with db.engine.connect() as connection:
        assert await connection.scalar(text("SELECT current_database()")) == test_settings.test_db_name
        assert await connection.scalar(text("SELECT current_user")) == test_settings.postgres_user
        assert await connection.scalar(text("SELECT version_num FROM alembic_version")) == "0001_greetings"
        assert await connection.scalar(text("SELECT count(*) FROM greetings")) == 0
```

Run through the existing Docker `tests` service before implementation; expect missing fixtures/modules. Do not run migrations against development to make this test pass.

- [ ] **Step 2: Add lazy database infrastructure and an explicit initial migration.**

`Database` uses `create_async_engine(settings.database_url, echo=False, hide_parameters=True, pool_pre_ping=True, connect_args={"timeout": 2, "command_timeout": 5})`; its session factory has `expire_on_commit=False`. Construction must not open a connection. `close()` awaits `engine.dispose()`.

`Greeting` is a SQLAlchemy declarative model named `greetings` with `Uuid(as_uuid=True)` primary key defaulting to `uuid4`, `String(100)` nonnullable name, and `DateTime(timezone=True)` nonnullable creation time with `server_default=func.now()`. Export `Base` for Alembic metadata. The revision implements:

```python
from alembic import op
import sqlalchemy as sa

revision = "0001_greetings"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "greetings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("char_length(name) BETWEEN 1 AND 100", name="ck_greetings_name_length"),
    )

def downgrade():
    op.drop_table("greetings")
```

Mirror the length constraint in model metadata. Generate `migrations/env.py` and `script.py.mako` using Alembic's async template in a temporary directory inside Docker, then adapt the env module to the interfaces below. Set `script_location = %(here)s/migrations` and omit credentials from `alembic.ini`.

The migration environment obtains a SQLAlchemy URL from `config.attributes["database_url"]`, falling back to `Settings().database_url` for ordinary Alembic commands. Its synchronous `apply_migrations(connection)` configures `context` with `Base.metadata` and runs migrations inside `context.begin_transaction()`. Its async entry creates an engine with `NullPool`, calls `connection.run_sync(apply_migrations)`, and disposes the engine in `finally`; the CLI enters it with `asyncio.run`. Offline generation uses the same URL object without printing it. Never format a password-bearing URL into `set_main_option`.

- [ ] **Step 3: Implement provisioning and admin commands.**

The provisioning service receives development credentials in its process environment and the test file at `/run/secrets/test-db.env`. Load only that mounted file with `python-dotenv`, require exactly `POSTGRES_USER` and `POSTGRES_PASSWORD`, and construct a fully validated `Settings` using explicit constructor overrides. Ordinary application and test processes never read dotenv files themselves:

```python
from pathlib import Path
from dotenv import dotenv_values
from template_fastapi_mcp.config import Settings

TEST_SECRET_PATH = Path("/run/secrets/test-db.env")

def load_test_settings(base_settings: Settings, secret_path: Path = TEST_SECRET_PATH) -> Settings:
    values = dotenv_values(secret_path)
    if set(values) != {"POSTGRES_USER", "POSTGRES_PASSWORD"}:
        raise ValueError("Invalid test credential file")
    user = values["POSTGRES_USER"]
    password = values["POSTGRES_PASSWORD"]
    if not isinstance(user, str) or not isinstance(password, str) or not user or not password:
        raise ValueError("Invalid test credential file")
    settings_data = base_settings.model_dump()
    settings_data.update(
        postgres_user=user,
        postgres_password=password,
        app_db_name=base_settings.test_db_name,
    )
    return Settings.model_validate(settings_data)
```

Provision only the selected test target using asyncpg, outside a transaction:

```python
import asyncpg
from pydantic import SecretStr
from template_fastapi_mcp.config import Settings

async def ensure_test_database(
    settings: Settings, *, admin_user: str, admin_password: SecretStr
) -> None:
    settings.assert_test_target()
    target_user = settings.postgres_user
    if target_user == admin_user:
        raise ValueError("Refusing to reuse the development login for tests")
    connection = await asyncpg.connect(
        host=settings.postgres_host, port=settings.postgres_port,
        user=admin_user, password=admin_password.get_secret_value(),
        database="postgres", timeout=5,
        server_settings={"log_statement": "none", "log_min_error_statement": "panic",
                         "log_min_duration_statement": "-1"},
    )
    try:
        owner = await connection.fetchval(
            "SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=$1",
            settings.test_db_name,
        )
        if owner is not None and owner != target_user:
            raise ValueError("Existing test database has a different owner")
        role = await connection.fetchrow(
            """SELECT oid, rolsuper, rolcreatedb, rolcreaterole, rolcanlogin,
                      rolinherit, rolreplication, rolbypassrls
                 FROM pg_roles WHERE rolname=$1""",
            target_user,
        )
        if role is not None:
            unsafe = (
                role["rolsuper"] or role["rolcreatedb"] or role["rolcreaterole"]
                or role["rolreplication"] or role["rolbypassrls"]
                or not role["rolcanlogin"] or role["rolinherit"]
            )
            has_memberships = await connection.fetchval(
                "SELECT EXISTS (SELECT 1 FROM pg_auth_members WHERE member=$1 OR roleid=$1)",
                role["oid"],
            )
            owns_other_database = await connection.fetchval(
                "SELECT EXISTS (SELECT 1 FROM pg_database WHERE datdba=$1 AND datname<>$2)",
                role["oid"], settings.test_db_name,
            )
            if unsafe or has_memberships or owns_other_database:
                raise ValueError("Refusing an unsafe existing test role")
        password_literal = await connection.fetchval(
            "SELECT quote_literal($1::text)", settings.postgres_password.get_secret_value()
        )
        if role is None:
            await connection.execute(
                f'CREATE ROLE "{target_user}" LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE '
                f'NOINHERIT NOREPLICATION NOBYPASSRLS PASSWORD {password_literal}'
            )
        else:
            await connection.execute(f'ALTER ROLE "{target_user}" PASSWORD {password_literal}')
        if owner is None:
            await connection.execute(f'CREATE DATABASE "{settings.test_db_name}" OWNER "{target_user}"')
    finally:
        await connection.close()
```

Interpolated identifiers require Task 2's strict name validation and target guards; PostgreSQL `quote_literal` safely quotes the password. The admin connection reads only development bootstrap credentials while the selected Settings hold test credentials. Require a distinct login, but do not require a `template_` prefix because the repository is meant to be copied and renamed. Refuse an existing role that cannot log in, inherits privileges, has superuser/database-creation/role-creation/replication/RLS-bypass attributes, has any role membership in either direction, owns any database other than the configured test database, or does not own an existing target database. Never print the role SQL or raw exceptions. Session logging controls prevent password-bearing role statements from being logged; all connections close in `finally`. Do not accept arbitrary database/role CLI arguments. There is no drop-database command.

Admin `migrate` selects the development service's application database and delegates to `run_migrations`. Admin `provision-test` loads development `Settings()` from its environment, calls `load_test_settings`, validates the returned test target, and calls `ensure_test_database(test_settings, admin_user=development.postgres_user, admin_password=development.postgres_password)`. Admin `test` runs inside the test-only container: validate its target, run migrations as the restricted test login, and launch pytest. It never receives development credentials. Return pytest's exit status; report credential-loading/provisioning/migration failures with a fixed sanitized message and a nonzero exit, and never launch tests after failure.

```python
import asyncio
import os
import subprocess
import sys
from alembic import command
from alembic.config import Config

def run_migrations(settings: Settings) -> None:
    config = Config("alembic.ini")
    config.attributes["database_url"] = settings.database_url
    command.upgrade(config, "head")

def run_tests(settings: Settings, pytest_args: list[str]) -> int:
    settings.assert_test_target()
    run_migrations(settings)
    child_env = dict(os.environ, APP_DB_NAME=settings.test_db_name)
    return subprocess.run([sys.executable, "-m", "pytest", *pytest_args], env=child_env).returncode
```

`main` uses argparse with a fixed choice of `migrate`, `provision-test`, or `test`; forward remaining pytest arguments for `test`. Catch anticipated setup errors at that CLI boundary without rendering their original strings/tracebacks. Only `provision-test` calls `load_test_settings` and then enters `asyncio.run(ensure_test_database(...))`. Exit via `raise SystemExit(main())`.

`bin/migrate` checks development credentials, starts/waits for `postgres`, then runs the app image with admin `migrate`, without starting the long-running app. `bin/test` checks both secret files and validates non-secret shared identity keys across dev/test configs, starts/waits for PostgreSQL using development interpolation, runs the one-shot `provision` service, then runs `tests` with only test credentials. Both forward user arguments exactly. Use these wrapper bodies after resolving `project_root` as in Task 1:

```bash
# bin/migrate
"$project_root/bin/check-secrets" dev
"$project_root/bin/compose" up -d --wait postgres
exec "$project_root/bin/compose" run --rm --no-deps app \
  python -m template_fastapi_mcp.admin migrate "$@"
```

```bash
# bin/test
"$project_root/bin/check-secrets" all
for setting in COMPOSE_PROJECT_NAME DEV_DB_NAME TEST_DB_NAME POSTGRES_HOST POSTGRES_PORT; do
  dev_value="$(awk -F= -v key="$setting" '$1 == key {print substr($0, index($0, "=") + 1)}' "$project_root/etc/dev/.env")"
  test_value="$(awk -F= -v key="$setting" '$1 == key {print substr($0, index($0, "=") + 1)}' "$project_root/etc/test/.env")"
  if [[ -z "$dev_value" || "$dev_value" != "$test_value" ]]; then
    printf 'Shared setting %s must match in dev and test configs\n' "$setting" >&2
    exit 2
  fi
  if [[ -n "${!setting:-}" && "${!setting}" != "$dev_value" ]]; then
    printf 'Shell override of shared setting %s is not supported\n' "$setting" >&2
    exit 2
  fi
done
"$project_root/bin/compose" up -d --wait postgres
"$project_root/bin/compose" --profile test \
  run --rm --no-deps provision python -m template_fastapi_mcp.admin provision-test
exec "$project_root/bin/compose" --environment test --profile test \
  run --rm --no-deps tests python -m template_fastapi_mcp.admin test "$@"
```

Keep the non-secret identity entries and secret `KEY=value` entries as unquoted single-line values, as shown in the examples. The host checker compares only presence, placeholders, permissions, and distinctness; it never sources or prints either secret. If an inherited shell value conflicts, fail before touching the database rather than selecting another Compose project.

- [ ] **Step 4: Add focused provisioning guard tests.**

Create `tests/unit/test_admin_guards.py` in this task. Define a database-free local `test_settings` fixture that constructs every required `Settings` field explicitly with distinct development/test database names and a selected test login; do not depend on the integration fixture added in Step 5 or on the container environment. `test_load_test_settings_uses_the_mounted_file` writes a two-key temporary dotenv file, calls `load_test_settings(test_settings.model_copy(update={"app_db_name": test_settings.dev_db_name}), path)`, and requires the returned settings to select `test_db_name` and the file's login without exposing its password in `repr`. `test_load_test_settings_rejects_missing_or_extra_keys` parametrizes missing user, missing password, an empty value, and an unexpected third key.

Use this pre-connect guard test as the concrete pattern:

```python
from unittest.mock import AsyncMock
import pytest
from pydantic import SecretStr
from template_fastapi_mcp.admin import ensure_test_database

@pytest.mark.anyio
async def test_provision_refuses_development_target(monkeypatch, test_settings):
    connect = AsyncMock()
    monkeypatch.setattr("template_fastapi_mcp.admin.asyncpg.connect", connect)
    wrong = test_settings.model_copy(update={"app_db_name": test_settings.dev_db_name})
    with pytest.raises(ValueError):
        await ensure_test_database(
            wrong, admin_user="dev_login",
            admin_password=SecretStr("admin-password"),
        )
    connect.assert_not_awaited()
```

Add `test_provision_refuses_equal_database_names` and `test_provision_refuses_reused_development_login` with the same `connect.assert_not_awaited()` assertion. For an existing role, mock the opened connection and parametrize `rolsuper`, `rolcreatedb`, `rolcreaterole`, `rolreplication`, `rolbypassrls`, `rolcanlogin=False`, `rolinherit=True`, `has_memberships=True`, and `owns_other_database=True`; name the test `test_provision_refuses_unsafe_existing_role`. In every case require the fixed `ValueError`, require no role/database mutation call, and await connection closure.

- [ ] **Step 5: Add fixtures that enforce isolation before cleanup.**

`test_settings` is an ordinary fixture loading `Settings()` from the test container environment, calling `assert_test_target()`, and returning those settings. It must reject a mistakenly selected development target rather than silently correcting it. `db` is an AnyIO async fixture: call `assert_test_target()` before opening a connection, construct `Database` inside that fixture's event loop, require `SELECT current_database()` and `SELECT current_user` to match the configured test database and login, delete only greeting rows before and after each test, and dispose the engine in `finally`. Unit tests do not request it, so there is no autouse database fixture. Do not use rollback-only fixtures for HTTP tests whose handlers commit separate sessions.

- [ ] **Step 6: Verify migration and target guards.**

```bash
bin/build
bin/test tests/unit tests/integration/test_database.py -q
bin/test tests/integration/test_database.py -q
```

Expected: repeatable success, migration remains at `0001_greetings`, every credential-loader and role-attribute guard test passes, and only the configured test database is touched. Migration application is idempotent. Checkpoint Task 3 files, including `tests/unit/test_admin_guards.py`.

## Task 4: Shared greeting persistence operations

**Files:** Create `greetings.py` and `tests/integration/test_greetings.py`; add a `greeting_service` fixture in `tests/conftest.py`.

**Interfaces:** Produces `GreetingService(db: Database)`, `async create(data: GreetingCreate) -> GreetingOut`, `async list(limit: int = 20) -> list[GreetingOut]`, and `StorageUnavailable`. Both transport adapters consume these exact interfaces.

- [ ] **Step 1: Write persistence and commit tests.**

```python
import pytest
from template_fastapi_mcp.schemas import GreetingCreate

@pytest.mark.anyio
@pytest.mark.integration
async def test_creation_commits_and_newest_is_first(greeting_service):
    first = await greeting_service.create(GreetingCreate(name="  First  "))
    second = await greeting_service.create(GreetingCreate(name="Second"))
    rows = await greeting_service.list(limit=1)
    assert first.name == "First"
    assert first.id != second.id
    assert rows[0].id == second.id
    assert len(rows) == 1
```

Run `bin/test tests/integration/test_greetings.py -q`; expect missing service initially. Separate transactions obtain separate PostgreSQL transaction timestamps; the tie test below covers identical times without relying on a sleep.

- [ ] **Step 2: Implement operation-owned transactions.**

```python
from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from template_fastapi_mcp.db import Database
from template_fastapi_mcp.models import Greeting
from template_fastapi_mcp.schemas import GreetingCreate, GreetingOut, Limit

class StorageUnavailable(Exception):
    pass

class GreetingService:
    def __init__(self, db: Database):
        self.db = db

    async def create(self, data: GreetingCreate) -> GreetingOut:
        try:
            async with self.db.sessions.begin() as session:
                row = Greeting(name=data.name)
                session.add(row)
                await session.flush()
                result = GreetingOut.model_validate(row)
            return result
        except (SQLAlchemyError, OSError, TimeoutError):
            raise StorageUnavailable("Greeting storage is unavailable") from None

    async def list(self, limit: int = 20) -> list[GreetingOut]:
        validated_limit = TypeAdapter(Limit).validate_python(limit)
        try:
            async with self.db.sessions() as session:
                statement = select(Greeting).order_by(
                    Greeting.created_at.desc(), Greeting.id.desc()
                ).limit(validated_limit)
                rows = (await session.scalars(statement)).all()
                return [GreetingOut.model_validate(row) for row in rows]
        except (SQLAlchemyError, OSError, TimeoutError):
            raise StorageUnavailable("Greeting storage is unavailable") from None
```

Do not log original database exception messages or their cause chains. Validation happens before SQL. The service's creation result is returned only after transaction commit succeeds.

- [ ] **Step 3: Cover ordering and boundary behavior with named cases.**

Add `test_uuid_breaks_timestamp_ties_newest_first`, inserting two rows at `2026-10-04T12:00:00Z` with UUIDs ending in `0001` and `0002` and requiring `0002` first. Add `test_duplicate_names_receive_distinct_ids`, `test_list_returns_empty_sequence`, and `test_list_accepts_boundary_limits_and_rejects_out_of_range`; accept 1 and 100 and require `ValidationError` for 0 and 101. Add `test_create_commits_before_return`, opening an independent session after `create` and selecting the returned UUID. Every test requests the guarded test-database fixture and asserts the exact IDs or returned sequence, not only row counts.

- [ ] **Step 4: Verify the service checkpoint.**

```bash
bin/test tests/unit tests/integration/test_database.py tests/integration/test_greetings.py -q
```

Expected: passing validation, migration, and persistence checks. Checkpoint Task 4 files.

## Task 5: REST routes and a database-independent application lifespan

**Files:** Create `api.py`, `main.py`, `tests/integration/test_rest.py`, `bin/up`, `bin/down`, and `bin/logs`; extend `compose.yaml` and `tests/conftest.py`.

**Interfaces:** Produces `build_router(service: GreetingService) -> APIRouter`, `create_app(settings: Settings | None = None) -> FastAPI`, and async test fixtures `rest_client` and `test_settings`. The factory keeps the database/service on `app.state.db` and `app.state.greetings`.

- [ ] **Step 1: Write the REST contract test.**

```python
import pytest

@pytest.mark.anyio
@pytest.mark.integration
async def test_rest_creation_and_listing(rest_client):
    created = await rest_client.post("/greetings", json={"name": "  Anar  "})
    assert created.status_code == 201
    greeting = created.json()
    assert greeting["name"] == "Anar"
    assert greeting["created_at"].endswith("Z")
    listed = await rest_client.get("/greetings", params={"limit": 1})
    assert listed.status_code == 200
    assert listed.json() == [greeting]
```

Run `bin/test tests/integration/test_rest.py -q`; expect missing factory/fixture initially.

- [ ] **Step 2: Implement the REST adapter.**

```python
from typing import Annotated
from fastapi import APIRouter, Query
from template_fastapi_mcp.greetings import GreetingService
from template_fastapi_mcp.schemas import GreetingCreate, GreetingOut

def build_router(service: GreetingService) -> APIRouter:
    router = APIRouter()

    @router.post("/greetings", status_code=201, response_model=GreetingOut)
    async def create_greeting(body: GreetingCreate) -> GreetingOut:
        return await service.create(body)

    @router.get("/greetings", response_model=list[GreetingOut])
    async def list_greetings(limit: Annotated[int, Query(ge=1, le=100)] = 20) -> list[GreetingOut]:
        return await service.list(limit)

    return router
```

The factory constructs a lazy `Database` and the shared service, includes this router, and adds `GET /health` returning only `{"status":"ok"}`. Use an async lifespan with `try/finally` to dispose the database. Do not connect to PostgreSQL or inspect schema during lifespan startup. Add a `StorageUnavailable` exception handler returning `JSONResponse(status_code=503, content={"detail":"Greeting storage is unavailable"})`. Do not enable debug error pages.

- [ ] **Step 3: Add explicit HTTPX lifespan fixtures and validation cases.**

```python
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from template_fastapi_mcp.main import create_app

@pytest.fixture
async def rest_client(db, test_settings):
    app = create_app(test_settings)
    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://localhost"
        ) as client:
            yield client
```

The fixture's database dependency cleans test rows but each factory owns its own engine. Add 422 tests for whitespace, length 101, a missing name, an extra field, and limits 0, 101, and `abc`. Verify `/docs` and `/openapi.json` remain accessible.

- [ ] **Step 4: Enable reload and expose ordinary developer commands.**

Set the app service command to:

```yaml
command: [uvicorn, "template_fastapi_mcp.main:create_app", --factory, --reload, --reload-dir, /workspace/src]
healthcheck:
  test:
    - CMD
    - python
    - -c
    - 'import os, urllib.request; urllib.request.urlopen("http://127.0.0.1:" + os.environ["UVICORN_PORT"] + "/health", timeout=2)'
  interval: 2s
  timeout: 3s
  retries: 30
```

Uvicorn reads `UVICORN_HOST` and `UVICORN_PORT` from the service env; watchfiles reads `WATCHFILES_FORCE_POLLING`. `bin/up` first runs `bin/check-secrets dev`, then runs `up -d --wait app`; `bin/down` runs `down` without `--volumes`; `bin/logs` defaults to `logs -f app postgres`. Do not add Inspector to the default log stream. Wrapper arguments remain forwarded where relevant.

- [ ] **Step 5: Verify REST and startup without migrating implicitly.**

```bash
bin/build
bin/test tests/integration/test_rest.py -q
bin/migrate
bin/up
```

Expected: tests pass, development migrations run only through the explicit command, app is healthy, and Swagger UI describes the greeting endpoints. Checkpoint Task 5 files.

## Task 6: MCP v2 tools and real Streamable HTTP transport

**Files:** Create `mcp_server.py`, `tests/helpers.py`, `tests/__init__.py`, `tests/integration/test_mcp.py`, and `tests/integration/test_cross_interface.py`; update `main.py` and `tests/conftest.py`.

**Interfaces:** Produces `build_mcp(service: GreetingService) -> MCPServer`; factory exposes `app.state.mcp`; async `live_server(settings: Settings, overrides: dict[str, str] | None = None)` context manager in `tests/helpers.py` and `live_url` fixture serve a dedicated test app over loopback inside the test container.

- [ ] **Step 1: Write a test that exercises modern and legacy HTTP connections.**

```python
import pytest
from mcp import Client

@pytest.mark.anyio
@pytest.mark.integration
@pytest.mark.parametrize("mode", ["auto", "legacy"])
async def test_mcp_tool_round_trip(live_url, mode):
    async with Client(live_url + "/mcp", mode=mode) as client:
        tools = await client.list_tools()
        assert {tool.name for tool in tools.tools} == {"create_greeting", "list_greetings"}
        created = await client.call_tool("create_greeting", {"name": "  Anar  "})
        assert not created.is_error
        assert created.structured_content["name"] == "Anar"
        listed = await client.call_tool("list_greetings", {"limit": 1})
        assert listed.structured_content["greetings"][0] == created.structured_content
        if mode == "auto":
            assert client.protocol_version == "2026-07-28"
        else:
            assert client.protocol_version == "2025-11-25"
```

Run `bin/test tests/integration/test_mcp.py -q`. Expected initially: no MCP endpoint or missing fixture. `auto` performs discovery; `legacy` forces the initialization handshake. Do not call removed v1 imports or manually initialize a v2 `Client`.

- [ ] **Step 2: Build the high-level v2 server and structured tool results.**

```python
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from template_fastapi_mcp.greetings import GreetingService, StorageUnavailable
from template_fastapi_mcp.schemas import GreetingCreate, GreetingList, GreetingOut, Limit, Name

def build_mcp(service: GreetingService) -> MCPServer:
    server = MCPServer("Greeting template")

    @server.tool(structured_output=True)
    async def create_greeting(name: Name) -> GreetingOut:
        """Store a greeting and return its identifier, name, and UTC creation time."""
        try:
            return await service.create(GreetingCreate(name=name))
        except StorageUnavailable:
            raise ToolError("Greeting storage is unavailable") from None

    @server.tool(structured_output=True)
    async def list_greetings(limit: Limit = 20) -> GreetingList:
        """Return up to 100 greetings, ordered newest first."""
        try:
            return GreetingList(greetings=await service.list(limit))
        except StorageUnavailable:
            raise ToolError("Greeting storage is unavailable") from None

    return server
```

The shared Pydantic annotations provide tool validation and output schemas. Verify schema constraints and the two advertised output shapes against the resolved SDK. SDK validation errors must stay anticipated tool errors; do not let a custom handler log a database cause chain.

- [ ] **Step 3: Wire the exact endpoint and owning lifespan.**

Create the SDK ASGI app before reading `session_manager`. Supply `TransportSecuritySettings` explicitly with hosts `localhost`, `localhost:*`, `127.0.0.1`, `127.0.0.1:*`, `app`, and `app:*`; origins include the configured localhost/127.0.0.1 app and Inspector URLs. Keep rebinding protection enabled. The Inspector backend and the test HTTP clients do not need browser CORS; do not add permissive wildcard CORS.

In the factory, set `app.state.mcp = build_mcp(app.state.greetings)`, construct its `streamable_http_app(json_response=True, stateless_http=True, transport_security=security)`, and mount it at `/` **after** FastAPI health/router/OpenAPI routes. Use one parent lifespan:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with server.session_manager.run():
            yield
    finally:
        await database.close()
```

Here `server` and `database` are the factory-local MCP server and database, captured by the lifespan closure. Stateless mode simplifies the legacy transport; modern requests are already sessionless. No SSE-only endpoint or stdio server is needed.

- [ ] **Step 4: Add the live test-server fixture with bounded readiness and teardown.**

`live_server` rejects a non-test target, copies the container environment, sets `APP_DB_NAME` to the test name, and accepts only `POSTGRES_HOST`/`POSTGRES_PORT` overrides for failure tests. Launch a separate Uvicorn process on `127.0.0.1:TEST_HTTP_PORT`, without reload. Poll `/health` for at most 10 seconds with 0.1-second intervals. Always terminate/wait; kill only that spawned child if it has not exited within 5 seconds. No published host port and no development app reuse.

Core process/readiness code inside this context manager:

```python
process = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "template_fastapi_mcp.main:create_app",
     "--factory", "--host", "127.0.0.1", "--port", str(settings.test_http_port)],
    env=child_env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
)
url = f"http://127.0.0.1:{settings.test_http_port}"
try:
    with anyio.fail_after(10):
        async with AsyncClient(timeout=0.5) as probe:
            while True:
                if process.poll() is not None:
                    raise RuntimeError("Test application exited before readiness")
                try:
                    response = await probe.get(url + "/health")
                    if response.status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                await anyio.sleep(0.1)
    yield url
finally:
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
```

Wrap it with `@asynccontextmanager`; imports are `anyio`, `httpx`, `subprocess`, `sys`, `os`, `AsyncClient`, and `asynccontextmanager`. `child_env` is the copied process environment plus the validated target and allowed overrides. Create empty `tests/__init__.py`; define the context manager in `tests/helpers.py` and import it into `conftest.py`. Define `live_url(db, test_settings)` to enter this context and yield its URL. The `db` fixture cleans greeting data around each live-server test.

- [ ] **Step 5: Test exact routing and transport security.**

Add `test_exact_mcp_route_does_not_redirect`. Send a legacy `initialize` JSON-RPC POST to `/mcp` using HTTPX with `follow_redirects=False`, `Accept: application/json, text/event-stream`, and protocol `2025-11-25`; require HTTP 200, an absent `Location` header, and a JSON-RPC result rather than a redirect. The payload is:

```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"route-test","version":"1"}}}
```

Add `test_mcp_host_allowlist`. Send the same request with `Host: untrusted.example` and require the SDK's rejection status; repeat with `Host: localhost`, `Host: 127.0.0.1:<test-port>`, and `Host: app:8000`, requiring each trusted host to reach the MCP handler. Assert statuses and response bodies without relying on server log text.

- [ ] **Step 6: Test MCP schemas and validation boundaries.**

Add `test_mcp_tool_schemas` and require both tools' `input_schema` and `output_schema` to be object-rooted. Assert the create input's trimmed-name length limit, the list input's 1/100 bounds and default 20, the create output's `id`, `name`, and `created_at` fields, and the list output's `greetings` array. Add `test_mcp_validation_boundaries`: call `create_greeting` with whitespace and 101 characters and require `is_error=True`; call `list_greetings` with 0 and 101 and require tool errors; call it with 1 and 100 and require successful structured `{"greetings": [...]}` results.

- [ ] **Step 7: Prove persistence across REST and MCP.**

In `tests/integration/test_cross_interface.py`, add `test_rest_and_mcp_share_persistence`. Use a real HTTPX client at `live_url` and an MCP `Client` at the same server. POST `Rest Name` through REST and require the same ID, name, and UTC timestamp in MCP listing; create `MCP Name` through MCP and require the same ID, name, and UTC timestamp in REST listing. Assert deterministic newest-first ordering and close both clients before fixture teardown.

- [ ] **Step 8: Verify the combined interface checkpoint.**

```bash
bin/build
bin/test tests/unit tests/integration -q
```

Expected: real modern/legacy MCP connections, exact route, schema/validation checks, REST and cross-interface checks pass. Checkpoint Task 6 files.

## Task 7: Failure behavior, cleanup, and development-data isolation

**Files:** Create `tests/integration/test_failures.py`; extend `tests/unit/test_admin_guards.py` and refine `admin.py` or fixtures only where these checks expose missing behavior.

**Interfaces:** Reuses `live_server`, `test_settings`, `db`, sanitized `StorageUnavailable`, and the existing CLI. No new service or database is introduced.

- [ ] **Step 1: Write the database-unavailable transport test.**

```python
import pytest
from httpx import AsyncClient
from mcp import Client
from tests.helpers import live_server

@pytest.mark.anyio
@pytest.mark.integration
async def test_health_survives_database_failure(db, test_settings):
    async with live_server(test_settings, {"POSTGRES_HOST": "127.0.0.1", "POSTGRES_PORT": "1"}) as url:
        async with AsyncClient(base_url=url, timeout=5) as rest:
            assert (await rest.get("/health")).json() == {"status": "ok"}
            response = await rest.post("/greetings", json={"name": "Anar"})
            assert response.status_code == 503
            assert response.json() == {"detail": "Greeting storage is unavailable"}
        async with Client(url + "/mcp") as mcp:
            failure = await mcp.call_tool("create_greeting", {"name": "Anar"})
            assert failure.is_error
            assert "Greeting storage is unavailable" in str(failure.content)
```

Use the `tests/helpers.py` helper introduced in Task 6. Run this specific test and fix only failures it demonstrates.

- [ ] **Step 2: Exercise missing schema and restoration without touching development.**

Before schema alteration call `test_settings.assert_test_target()` and check `current_database()`. Rename the test table to `greetings_unavailable`, call REST creation/listing and MCP creation/listing through the live server, and require sanitized errors while health succeeds. Restore the table in `finally` before the `db` fixture's row cleanup. The database and development app stay running throughout.

```python
async with db.engine.begin() as connection:
    await connection.execute(text("ALTER TABLE greetings RENAME TO greetings_unavailable"))
try:
    await check_missing_schema_responses(url)
finally:
    async with db.engine.begin() as connection:
        await connection.execute(text("ALTER TABLE greetings_unavailable RENAME TO greetings"))
```

Define `check_missing_schema_responses(url: str) -> None` in `test_failures.py`: an async HTTPX client requires both REST routes to return 503; an MCP client calls both tools and requires `is_error=True`; health returns 200. Compare messages against the fixed sanitized text and require no `asyncpg`, `postgresql`, SQL statement, or configured password in responses. This helper is part of the test, not application code.

- [ ] **Step 3: Verify CLI failure propagation and resource cleanup.**

Extend the Task 3 guard file with `test_run_tests_preserves_pytest_exit_status`, mocking `run_migrations` and `subprocess.run` and requiring the exact nonzero child return code. Add `test_test_command_does_not_launch_pytest_after_migration_failure`, making `run_migrations` raise an anticipated setup exception and asserting `subprocess.run` is untouched. Add `test_provision_command_does_not_connect_after_secret_loading_failure`, making `load_test_settings` fail and asserting `asyncpg.connect` is untouched. None of these tests may open a real database connection or render exception strings containing credentials.

Run the live transport tests repeatedly using two separate `bin/test` invocations; require no leftover child process, occupied `TEST_HTTP_PORT`, or event-loop errors. Tests are serial; do not install pytest-xdist for this template.

- [ ] **Step 4: Verify the failure-handling checkpoint.**

```bash
bin/build
bin/test tests/unit tests/integration -q
bin/test tests/integration/test_failures.py tests/integration/test_mcp.py -q
```

Expected: the development PostgreSQL service is never stopped, all failure responses are sanitized, and subsequent tests succeed after schema restoration. Checkpoint Task 7 files.

## Task 8: Inspector, documented commands, and clean-checkout acceptance

**Files:** Extend `compose.yaml`; create `bin/inspector` and `README.md`; refine the existing wrappers only as needed for the documented flow.

**Interfaces:** Inspector's browser UI is `http://localhost:6274` by default; its server target is `http://app:8000/mcp`. Port values come from `etc/dev/.env`. README maps every wrapper to its purpose and identifies rebuild/recreate/migration boundaries.

- [ ] **Step 1: Add the optional Inspector service.**

```yaml
inspector:
  image: ${INSPECTOR_IMAGE}
  profiles: [inspector]
  env_file: [etc/dev/.env]
  command: [--web]
  ports: ["127.0.0.1:${CLIENT_PORT}:${CLIENT_PORT}"]
  depends_on:
    app:
      condition: service_healthy
  logging:
    driver: none
```

The official image's entrypoint is `mcp-inspector`; launch the web UI detached. Inspector generates its own token and injects it into the served page, so the user can browse the plain localhost URL. Its startup banner includes that token; `logging.driver: none` prevents Docker from recording it. Do not disable UI authentication, pass database secrets to Inspector, or emit a token-bearing URL from the wrapper. Default `bin/logs` covers app and PostgreSQL only.

`bin/inspector` runs `bin/compose --profile inspector up -d --wait inspector`, then prints only the non-secret browser URL. There is no old proxy port 6277. The greeting template does not provide MCP Apps, so publishing sandbox/app-origin ports is unnecessary. Avoid a broad CORS workaround when connection errors are actually Host allowlist failures.

- [ ] **Step 2: Write the README with runnable first-run and test commands.**

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

Explain that the committed lockfile makes `bin/lock` unnecessary for ordinary checkout setup; use it after dependency edits, then `bin/build` and recreate affected containers. Explain how `bin/init` copies the separate `etc/dev/.env.example`, `etc/test/.env.example`, and each environment's `secrets/.env.sample` without overwriting existing values. Both secret copies use `POSTGRES_USER` and `POSTGRES_PASSWORD`, but the developer must replace placeholders with different development and test values before running `bin/up`, `bin/migrate`, or `bin/test`. Explain that changing development credentials does not reinitialize a persisted PostgreSQL volume and that guarded provisioning updates only the configured test role's password without changing development roles or data. Credentials must never appear in README examples beyond the literal placeholder values, command arguments, or diagnostic output.

Add a **Copy and rename this template** checklist before first-run instructions. It names every coordinated rename surface: repository directory, `[project].name`, import package directory and imports, Compose project and image names, development/test database names, default sample login names, README title/examples, and Python module references in Compose/Uvicorn commands. Instruct the developer to rename the checked-in examples and samples before `bin/init`; no provisioning rule may require the original `template_fastapi_mcp` or `template_` strings after those coordinated edits.

State the prerequisite as Docker Engine with the `docker compose` plugin and `compose up --wait` support (Compose 2.17 or newer). Tell users to verify it with `docker compose version`; the wrappers deliberately do not fall back to legacy `docker-compose` v1.

Document `/health`, `/docs`, REST request/response examples, `/mcp`, and both tool signatures. In Inspector, add a Streamable HTTP server with Compose target `http://app:8000/mcp`, connect, create `Anar`, and list it. Explain the difference between that internal target and the host URL `http://localhost:8000/mcp`.

Document source hot reload, editable import paths, dependency rebuilds, environment recreations, and explicit schema migrations. Document `bin/down` as preserving data; do not offer an automatic volume reset. Include troubleshooting for unhealthy PostgreSQL, missing migrations, invalid MCP Host/Origin, stale lockfiles, and missing/placeholder credentials, using sanitized diagnostics.

- [ ] **Step 3: Verify environment independence and persistence.**

From `/tmp`, invoke the wrappers by their absolute project paths and confirm paths still resolve. Ordinary checks use `bin/compose config --quiet` and `bin/compose ps`; do not print resolved secrets.

Use the normal development REST interface to create an acceptance greeting and record its UUID. Run the complete `bin/test -q`, then list development greetings and require that UUID to remain. This is a manual development acceptance flow; automated test fixtures never seed or clean the development database. Restart using `bin/down` followed by `bin/up` and require the same greeting to remain. Do not run the development preservation check by overriding the test database target.

- [ ] **Step 4: Verify live reload, import resolution, and stale-lock rejection.**

1. Run the Task 1 module-path command and require `/workspace/src/`.
2. Make a temporary local source edit to the `/health` handler's response, verify the running container serves it after reload, then restore that exact edit and verify the original response. Do not overwrite unrelated edits or rebuild the image during this check.
3. In a temporary copy of the project, change metadata to add a dependency without updating `uv.lock` and build the development stage with the same args. Require a stale-lockfile failure. Preserve the original files; the temporary copy must exclude secrets. Use the bootstrap service to copy/check files if scripting requires Python, rather than invoking host Python.
4. Confirm no local `.venv` or secret file is required in the image, and Inspector's Docker log driver is `none`. Inspect only that non-secret field, never the complete container environment.

- [ ] **Step 5: Run the final acceptance checkpoint and hand off.**

```bash
bin/build
bin/test -q
bin/compose config --quiet
bin/compose ps
```

Expected: full tests pass, Compose configuration validates, app/PostgreSQL are healthy, the manual Inspector create/list flow succeeds, and mounted source reload is demonstrated. Record exact test totals and any manual check not performed. Do not claim Inspector or reload verification based on a configuration review alone. Checkpoint Task 8 files and hand off the runnable commands.

## Spec coverage and review checklist

| Requirement | Implementation | Verification |
| --- | --- | --- |
| Docker-only dependencies and commands | Task 1 | Bootstrap, lock, build; no host Python |
| Separate dev/test config and secret files | Tasks 1–3, 8 | Idempotent init, distinct logins, explicit selection, masked mounts, ignored secrets |
| Mounted source, external venv, automatic reload | Tasks 1, 5 | Editable import path and Task 8 source-edit check |
| Dedicated test DB/login on shared PostgreSQL | Task 3 | Database/login identity, restricted role, provisioning guards |
| Explicit migrations and named-volume persistence | Tasks 3, 8 | Repeat migration, restart/preservation checks |
| Shared validation, UUIDs, UTC, deterministic ordering | Tasks 2, 4 | Boundary, serialization, commit, tie tests |
| REST health/create/list and statuses | Task 5 | HTTPX lifespan, REST validation checks |
| MCP v2, exact `/mcp`, modern/legacy HTTP | Task 6 | Real Uvicorn/SDK connections and no-redirect check |
| Shared REST/MCP persistence | Task 6 | Both directions through one live test server |
| Database-independent health and sanitized failures | Task 7 | Unreachable target and missing-table checks |
| Inspector over Compose network on localhost UI | Task 8 | Manual UI connection and create/list |
| Development data survives tests and shutdown | Tasks 3, 7–8 | Guards, restoration, manual UUID preservation |

## Reference checks used for this plan

- [uv Docker integration](https://docs.astral.sh/uv/guides/integration/docker/): locked sync and editable imports.
- [FastAPI async tests](https://fastapi.tiangolo.com/advanced/async-tests/): explicit HTTPX lifespan management.
- [Alembic async migrations](https://alembic.sqlalchemy.org/en/latest/cookbook.html#using-asyncio-with-alembic): async engine plus synchronous migration callback.
- [MCP SDK ASGI integration](https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/run/asgi.md) and [transport settings](https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/run/deploy.md): mounting, lifespan, and Host/Origin allowlists.
- [MCP v2 migration](https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/migration.md): v2 names, Python snake-case result fields, and legacy compatibility.
- [Inspector release](https://github.com/modelcontextprotocol/inspector/releases/tag/2.9.0), [Dockerfile](https://github.com/modelcontextprotocol/inspector/blob/main/Dockerfile), and [web configuration](https://github.com/modelcontextprotocol/inspector/blob/main/clients/web/server/web-server-config.ts): version pin, entrypoint, and token banner.
- [Official Python image tags](https://github.com/docker-library/official-images/blob/master/library/python) and [PostgreSQL image tags](https://github.com/docker-library/official-images/blob/master/library/postgres): selected exact image versions. Confirm their manifests at Task 1 execution; do not substitute floating tags if a pull fails.

- [PostgreSQL role options](https://www.postgresql.org/docs/17/sql-createrole.html) and [statement logging](https://www.postgresql.org/docs/17/runtime-config-logging.html): restricted test roles and password-safe provisioning diagnostics.
