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
                statement = (
                    select(Greeting)
                    .order_by(Greeting.created_at.desc(), Greeting.id.desc())
                    .limit(validated_limit)
                )
                rows = (await session.scalars(statement)).all()
                return [GreetingOut.model_validate(row) for row in rows]
        except (SQLAlchemyError, OSError, TimeoutError):
            raise StorageUnavailable("Greeting storage is unavailable") from None
