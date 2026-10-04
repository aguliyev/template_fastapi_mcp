import pytest
from sqlalchemy import text


@pytest.mark.anyio
@pytest.mark.integration
async def test_migrated_database_is_test_database(db, test_settings):
    async with db.engine.connect() as connection:
        assert (
            await connection.scalar(text("SELECT current_database()"))
            == test_settings.test_db_name
        )
        assert (
            await connection.scalar(text("SELECT current_user"))
            == test_settings.postgres_user
        )
        assert (
            await connection.scalar(text("SELECT version_num FROM alembic_version"))
            == "0001_greetings"
        )
        assert await connection.scalar(text("SELECT count(*) FROM greetings")) == 0
