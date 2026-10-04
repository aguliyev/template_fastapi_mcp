from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import sys
from pathlib import Path

import asyncpg
from alembic import command
from alembic.config import Config
from dotenv import dotenv_values
from pydantic import SecretStr

from template_fastapi_mcp.config import Settings

TEST_SECRET_PATH = Path("/run/secrets/test-db.env")


def load_test_settings(
    base_settings: Settings, secret_path: Path = TEST_SECRET_PATH
) -> Settings:
    values = dotenv_values(secret_path)
    if set(values) != {"POSTGRES_USER", "POSTGRES_PASSWORD"}:
        raise ValueError("Invalid test credential file")
    user = values["POSTGRES_USER"]
    password = values["POSTGRES_PASSWORD"]
    if (
        not isinstance(user, str)
        or not isinstance(password, str)
        or not user
        or not password
    ):
        raise ValueError("Invalid test credential file")
    settings_data = base_settings.model_dump()
    settings_data.update(
        postgres_user=user,
        postgres_password=password,
        app_db_name=base_settings.test_db_name,
    )
    return Settings.model_validate(settings_data)


async def ensure_test_database(
    settings: Settings, *, admin_user: str, admin_password: SecretStr
) -> None:
    settings.assert_test_target()
    target_user = settings.postgres_user
    if target_user == admin_user:
        raise ValueError("Refusing to reuse the development login for tests")
    connection = await asyncpg.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        user=admin_user,
        password=admin_password.get_secret_value(),
        database="postgres",
        timeout=5,
        server_settings={
            "log_statement": "none",
            "log_min_error_statement": "panic",
            "log_min_duration_statement": "-1",
        },
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
                role["rolsuper"]
                or role["rolcreatedb"]
                or role["rolcreaterole"]
                or role["rolreplication"]
                or role["rolbypassrls"]
                or not role["rolcanlogin"]
                or role["rolinherit"]
            )
            has_memberships = await connection.fetchval(
                "SELECT EXISTS (SELECT 1 FROM pg_auth_members WHERE member=$1 OR roleid=$1)",
                role["oid"],
            )
            owns_other_database = await connection.fetchval(
                "SELECT EXISTS (SELECT 1 FROM pg_database WHERE datdba=$1 AND datname<>$2)",
                role["oid"],
                settings.test_db_name,
            )
            if unsafe or has_memberships or owns_other_database:
                raise ValueError("Refusing an unsafe existing test role")
        password_literal = await connection.fetchval(
            "SELECT quote_literal($1::text)",
            settings.postgres_password.get_secret_value(),
        )
        if role is None:
            await connection.execute(
                f'CREATE ROLE "{target_user}" LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE '
                f"NOINHERIT NOREPLICATION NOBYPASSRLS PASSWORD {password_literal}"
            )
        else:
            await connection.execute(
                f'ALTER ROLE "{target_user}" PASSWORD {password_literal}'
            )
        if owner is None:
            await connection.execute(
                f'CREATE DATABASE "{settings.test_db_name}" OWNER "{target_user}"'
            )
    finally:
        await connection.close()


def run_migrations(settings: Settings) -> None:
    config = Config("alembic.ini")
    config.attributes["database_url"] = settings.database_url
    command.upgrade(config, "head")


def run_tests(settings: Settings, pytest_args: list[str]) -> int:
    settings.assert_test_target()
    run_migrations(settings)
    child_env = dict(os.environ, APP_DB_NAME=settings.test_db_name)
    return subprocess.run(
        [sys.executable, "-m", "pytest", *pytest_args], env=child_env
    ).returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="template_fastapi_mcp.admin")
    parser.add_argument("command", choices=["migrate", "provision-test", "test"])
    args, rest = parser.parse_known_args(argv)
    try:
        if args.command == "migrate":
            run_migrations(Settings())
        elif args.command == "provision-test":
            development = Settings()
            test_settings = load_test_settings(development)
            test_settings.assert_test_target()
            asyncio.run(
                ensure_test_database(
                    test_settings,
                    admin_user=development.postgres_user,
                    admin_password=development.postgres_password,
                )
            )
        elif args.command == "test":
            settings = Settings()
            settings.assert_test_target()
            return run_tests(settings, rest)
    except Exception:
        print(f"admin {args.command} failed", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
