import pytest
from sqlalchemy import text


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def test_settings():
    from app.config import Settings

    settings = Settings()
    settings.assert_test_target()
    return settings


@pytest.fixture
async def db(test_settings):
    from app.db import Database

    test_settings.assert_test_target()
    database = Database(test_settings)
    try:
        async with database.engine.connect() as connection:
            assert (
                await connection.scalar(text("SELECT current_database()"))
                == test_settings.test_db_name
            )
            assert (
                await connection.scalar(text("SELECT current_user"))
                == test_settings.postgres_user
            )
        async with database.engine.begin() as connection:
            await connection.execute(text("DELETE FROM greetings"))
        yield database
    finally:
        try:
            async with database.engine.begin() as connection:
                await connection.execute(text("DELETE FROM greetings"))
        finally:
            await database.close()


@pytest.fixture
async def greeting_service(db):
    from app.greetings import GreetingService

    return GreetingService(db)


@pytest.fixture
async def rest_client(db, test_settings):
    from asgi_lifespan import LifespanManager
    from httpx import ASGITransport, AsyncClient

    from app.main import create_app

    app = create_app(test_settings)
    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://localhost"
        ) as client:
            yield client


@pytest.fixture
async def live_url(db, test_settings):
    from tests.helpers import live_server

    async with live_server(test_settings) as url:
        yield url
