from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_serializer,
)

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
