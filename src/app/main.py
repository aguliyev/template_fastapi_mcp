from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from mcp.server.transport_security import TransportSecuritySettings

from app.api import build_router
from app.config import Settings
from app.db import Database
from app.greetings import GreetingService, StorageUnavailable
from app.mcp_server import build_mcp


def _transport_security(settings: Settings) -> TransportSecuritySettings:
    return TransportSecuritySettings(
        allowed_hosts=[
            "localhost",
            "localhost:*",
            "127.0.0.1",
            "127.0.0.1:*",
            "app",
            "app:*",
        ],
        allowed_origins=[
            f"http://localhost:{settings.app_port}",
            f"http://127.0.0.1:{settings.app_port}",
            f"http://localhost:{settings.client_port}",
            f"http://127.0.0.1:{settings.client_port}",
        ],
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or Settings()
    database = Database(resolved)
    service = GreetingService(database)
    server = build_mcp(service)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            async with server.session_manager.run():
                yield
        finally:
            await database.close()

    app = FastAPI(lifespan=lifespan)
    app.state.db = database
    app.state.greetings = service
    app.state.mcp = server
    app.include_router(build_router(service))

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.exception_handler(StorageUnavailable)
    async def storage_unavailable(request, exc):
        return JSONResponse(
            status_code=503, content={"detail": "Greeting storage is unavailable"}
        )

    mcp_app = server.streamable_http_app(
        json_response=True,
        stateless_http=True,
        transport_security=_transport_security(resolved),
    )
    app.mount("/", mcp_app)

    return app
