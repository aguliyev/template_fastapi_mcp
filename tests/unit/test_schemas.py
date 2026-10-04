from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest
from pydantic import TypeAdapter, ValidationError

from template_fastapi_mcp.schemas import GreetingCreate, GreetingOut, Limit


def test_name_is_trimmed():
    assert GreetingCreate(name="  Anar\t").name == "Anar"


@pytest.mark.parametrize("name", ["", " \t\n", "a" * 101, None, 123])
def test_invalid_names(name):
    with pytest.raises(ValidationError):
        GreetingCreate(name=name)


def test_trimmed_length_boundary():
    assert len(GreetingCreate(name=" " + "a" * 100 + " ").name) == 100


def test_greeting_out_serializes_uuid_and_converts_aware_timestamp_to_utc():
    greeting = GreetingOut(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        name="Anar",
        created_at=datetime(2026, 10, 4, 7, 0, 0, tzinfo=ZoneInfo("America/Chicago")),
    )
    dumped = greeting.model_dump(mode="json")
    assert dumped["id"] == "00000000-0000-0000-0000-000000000001"
    assert dumped["created_at"] == "2026-10-04T12:00:00Z"


def test_greeting_out_rejects_naive_timestamp():
    with pytest.raises(ValidationError):
        GreetingOut(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            name="Anar",
            created_at=datetime(2026, 10, 4, 12, 0, 0),
        )


def test_limit_boundaries():
    adapter = TypeAdapter(Limit)
    assert adapter.validate_python(1) == 1
    assert adapter.validate_python(100) == 100
    with pytest.raises(ValidationError):
        adapter.validate_python(0)
    with pytest.raises(ValidationError):
        adapter.validate_python(101)
