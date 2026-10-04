from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.models import Greeting
from app.schemas import GreetingCreate


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


@pytest.mark.anyio
@pytest.mark.integration
async def test_uuid_breaks_timestamp_ties_newest_first(greeting_service, db):
    moment = datetime(2026, 10, 4, 12, 0, 0, tzinfo=ZoneInfo("UTC"))
    async with db.sessions.begin() as session:
        session.add(
            Greeting(
                id=UUID("00000000-0000-0000-0000-000000000001"),
                name="Tie One",
                created_at=moment,
            )
        )
        session.add(
            Greeting(
                id=UUID("00000000-0000-0000-0000-000000000002"),
                name="Tie Two",
                created_at=moment,
            )
        )
    rows = await greeting_service.list(limit=10)
    assert [row.name for row in rows] == ["Tie Two", "Tie One"]


@pytest.mark.anyio
@pytest.mark.integration
async def test_duplicate_names_receive_distinct_ids(greeting_service):
    first = await greeting_service.create(GreetingCreate(name="Anar"))
    second = await greeting_service.create(GreetingCreate(name="Anar"))
    assert first.id != second.id
    assert first.name == second.name == "Anar"


@pytest.mark.anyio
@pytest.mark.integration
async def test_list_returns_empty_sequence(greeting_service):
    assert await greeting_service.list() == []


@pytest.mark.anyio
@pytest.mark.integration
async def test_list_accepts_boundary_limits_and_rejects_out_of_range(
    greeting_service,
):
    await greeting_service.create(GreetingCreate(name="Anar"))
    assert len(await greeting_service.list(limit=1)) == 1
    assert len(await greeting_service.list(limit=100)) == 1
    with pytest.raises(ValidationError):
        await greeting_service.list(limit=0)
    with pytest.raises(ValidationError):
        await greeting_service.list(limit=101)


@pytest.mark.anyio
@pytest.mark.integration
async def test_create_commits_before_return(greeting_service, db):
    created = await greeting_service.create(GreetingCreate(name="Anar"))
    async with db.sessions() as session:
        row = await session.scalar(
            select(Greeting).where(Greeting.id == created.id)
        )
        assert row is not None
        assert row.name == "Anar"
