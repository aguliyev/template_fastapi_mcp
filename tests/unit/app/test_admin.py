from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import SecretStr

import app.admin as admin_module
from app.admin import ensure_test_database, load_test_settings
from app.config import Settings


@pytest.fixture
def test_settings():
    return Settings.model_validate(
        {
            "postgres_host": "postgres",
            "postgres_port": 5432,
            "postgres_user": "guard_test_app",
            "postgres_password": "guard-test-password",
            "dev_db_name": "guard_dev_db",
            "test_db_name": "guard_test_db",
            "app_db_name": "guard_test_db",
            "app_port": 8000,
            "uvicorn_port": 8000,
            "test_http_port": 18000,
            "client_port": 6274,
        }
    )


def test_load_test_settings_uses_the_mounted_file(tmp_path, test_settings):
    secret_file = tmp_path / "test-db.env"
    secret_file.write_text("POSTGRES_USER=file_login\nPOSTGRES_PASSWORD=file-password\n")
    base = test_settings.model_copy(update={"app_db_name": test_settings.dev_db_name})
    loaded = load_test_settings(base, secret_file)
    assert loaded.app_db_name == test_settings.test_db_name
    assert loaded.postgres_user == "file_login"
    assert "file-password" not in repr(loaded)


@pytest.mark.parametrize(
    "content",
    [
        "POSTGRES_PASSWORD=file-password\n",
        "POSTGRES_USER=file_login\n",
        "POSTGRES_USER=\nPOSTGRES_PASSWORD=file-password\n",
        "POSTGRES_USER=file_login\nPOSTGRES_PASSWORD=file-password\nEXTRA=1\n",
    ],
)
def test_load_test_settings_rejects_missing_or_extra_keys(
    tmp_path, test_settings, content
):
    secret_file = tmp_path / "test-db.env"
    secret_file.write_text(content)
    with pytest.raises(ValueError, match="Invalid test credential file"):
        load_test_settings(test_settings, secret_file)


@pytest.mark.anyio
async def test_provision_refuses_development_target(monkeypatch, test_settings):
    connect = AsyncMock()
    monkeypatch.setattr("app.admin.asyncpg.connect", connect)
    wrong = test_settings.model_copy(update={"app_db_name": test_settings.dev_db_name})
    with pytest.raises(ValueError):
        await ensure_test_database(
            wrong,
            admin_user="dev_login",
            admin_password=SecretStr("admin-password"),
        )
    connect.assert_not_awaited()


@pytest.mark.anyio
async def test_provision_refuses_equal_database_names(monkeypatch, test_settings):
    connect = AsyncMock()
    monkeypatch.setattr("app.admin.asyncpg.connect", connect)
    wrong = test_settings.model_copy(
        update={
            "dev_db_name": "same_db",
            "test_db_name": "same_db",
            "app_db_name": "same_db",
        }
    )
    with pytest.raises(ValueError):
        await ensure_test_database(
            wrong,
            admin_user="dev_login",
            admin_password=SecretStr("admin-password"),
        )
    connect.assert_not_awaited()


@pytest.mark.anyio
async def test_provision_refuses_reused_development_login(monkeypatch, test_settings):
    connect = AsyncMock()
    monkeypatch.setattr("app.admin.asyncpg.connect", connect)
    with pytest.raises(ValueError):
        await ensure_test_database(
            test_settings,
            admin_user=test_settings.postgres_user,
            admin_password=SecretStr("admin-password"),
        )
    connect.assert_not_awaited()


def _safe_role(**overrides):
    role = {
        "oid": 4242,
        "rolsuper": False,
        "rolcreatedb": False,
        "rolcreaterole": False,
        "rolcanlogin": True,
        "rolinherit": False,
        "rolreplication": False,
        "rolbypassrls": False,
    }
    role.update(overrides)
    return role


def _connection_mock(owner=None, role=None, memberships=False, owns_other=False):
    connection = AsyncMock()

    async def fetchval(query, *args):
        if "pg_get_userbyid" in query:
            return owner
        if "pg_auth_members" in query:
            return memberships
        if "quote_literal" in query:
            return "'quoted-password'"
        return owns_other

    connection.fetchval.side_effect = fetchval
    connection.fetchrow.return_value = role
    return connection


@pytest.mark.anyio
@pytest.mark.parametrize(
    "role_kwargs,memberships,owns_other",
    [
        ({"rolsuper": True}, False, False),
        ({"rolcreatedb": True}, False, False),
        ({"rolcreaterole": True}, False, False),
        ({"rolreplication": True}, False, False),
        ({"rolbypassrls": True}, False, False),
        ({"rolcanlogin": False}, False, False),
        ({"rolinherit": True}, False, False),
        ({}, True, False),
        ({}, False, True),
    ],
)
async def test_provision_refuses_unsafe_existing_role(
    monkeypatch, test_settings, role_kwargs, memberships, owns_other
):
    connect = AsyncMock()
    connection = _connection_mock(
        owner=None,
        role=_safe_role(**role_kwargs),
        memberships=memberships,
        owns_other=owns_other,
    )
    connect.return_value = connection
    monkeypatch.setattr("app.admin.asyncpg.connect", connect)
    with pytest.raises(ValueError):
        await ensure_test_database(
            test_settings,
            admin_user="dev_login",
            admin_password=SecretStr("admin-password"),
        )
    connection.execute.assert_not_awaited()
    connection.close.assert_awaited()


def test_run_tests_preserves_pytest_exit_status(monkeypatch, test_settings):
    monkeypatch.setattr(admin_module, "run_migrations", lambda settings: None)
    completed = MagicMock()
    completed.returncode = 3
    launched = MagicMock(return_value=completed)
    monkeypatch.setattr(admin_module.subprocess, "run", launched)
    assert admin_module.run_tests(test_settings, ["tests/unit", "-q"]) == 3
    launched.assert_called_once()


def test_test_command_does_not_launch_pytest_after_migration_failure(
    monkeypatch, test_settings
):
    def fail_migrations(settings):
        raise ValueError("migration unavailable")

    monkeypatch.setattr(admin_module, "run_migrations", fail_migrations)
    launched = MagicMock()
    monkeypatch.setattr(admin_module.subprocess, "run", launched)
    with pytest.raises(ValueError):
        admin_module.run_tests(test_settings, ["tests/unit"])
    launched.assert_not_called()


def test_provision_command_does_not_connect_after_secret_loading_failure(
    monkeypatch, test_settings
):
    def fail_loading(base_settings, secret_path=admin_module.TEST_SECRET_PATH):
        raise ValueError("Invalid test credential file")

    monkeypatch.setattr(admin_module, "load_test_settings", fail_loading)
    connect = AsyncMock()
    monkeypatch.setattr(admin_module.asyncpg, "connect", connect)
    assert admin_module.main(["provision-test"]) == 1
    connect.assert_not_awaited()
