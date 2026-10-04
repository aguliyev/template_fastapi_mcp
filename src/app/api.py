from typing import Annotated

from fastapi import APIRouter, Query

from app.greetings import GreetingService
from app.schemas import GreetingCreate, GreetingOut


def build_router(service: GreetingService) -> APIRouter:
    router = APIRouter()

    @router.post("/greetings", status_code=201, response_model=GreetingOut)
    async def create_greeting(body: GreetingCreate) -> GreetingOut:
        return await service.create(body)

    @router.get("/greetings", response_model=list[GreetingOut])
    async def list_greetings(
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
    ) -> list[GreetingOut]:
        return await service.list(limit)

    return router
