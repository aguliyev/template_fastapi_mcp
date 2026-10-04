import pytest
from httpx import AsyncClient
from mcp import Client
from sqlalchemy import text

from tests.helpers import live_server

SANITIZED = "Greeting storage is unavailable"


async def check_missing_schema_responses(url: str, test_settings=None) -> None:
    forbidden = ["asyncpg", "postgresql", "SELECT", "CREATE"]
    if test_settings is not None:
        forbidden.append(test_settings.postgres_password.get_secret_value())
    async with AsyncClient(base_url=url, timeout=5) as rest:
        assert (await rest.get("/health")).json() == {"status": "ok"}
        created = await rest.post("/greetings", json={"name": "Anar"})
        assert created.status_code == 503
        assert created.json() == {"detail": SANITIZED}
        listed = await rest.get("/greetings")
        assert listed.status_code == 503
        assert listed.json() == {"detail": SANITIZED}
    async with Client(url + "/mcp") as mcp:
        create_failure = await mcp.call_tool("create_greeting", {"name": "Anar"})
        assert create_failure.is_error
        list_failure = await mcp.call_tool("list_greetings", {"limit": 20})
        assert list_failure.is_error
        for failure in (create_failure, list_failure):
            body = str(failure.content)
            assert SANITIZED in body
            for secret in forbidden:
                assert secret not in body


@pytest.mark.anyio
@pytest.mark.integration
async def test_health_survives_database_failure(db, test_settings):
    async with live_server(
        test_settings, {"POSTGRES_HOST": "127.0.0.1", "POSTGRES_PORT": "1"}
    ) as url:
        async with AsyncClient(base_url=url, timeout=5) as rest:
            assert (await rest.get("/health")).json() == {"status": "ok"}
            response = await rest.post("/greetings", json={"name": "Anar"})
            assert response.status_code == 503
            assert response.json() == {"detail": SANITIZED}
        async with Client(url + "/mcp") as mcp:
            failure = await mcp.call_tool("create_greeting", {"name": "Anar"})
            assert failure.is_error
            assert SANITIZED in str(failure.content)


@pytest.mark.anyio
@pytest.mark.integration
async def test_missing_schema_returns_sanitized_errors(db, test_settings):
    test_settings.assert_test_target()
    async with db.engine.connect() as connection:
        assert (
            await connection.scalar(text("SELECT current_database()"))
            == test_settings.test_db_name
        )
    async with live_server(test_settings) as url:
        async with db.engine.begin() as connection:
            await connection.execute(
                text("ALTER TABLE greetings RENAME TO greetings_unavailable")
            )
        try:
            await check_missing_schema_responses(url, test_settings)
        finally:
            async with db.engine.begin() as connection:
                await connection.execute(
                    text("ALTER TABLE greetings_unavailable RENAME TO greetings")
                )
