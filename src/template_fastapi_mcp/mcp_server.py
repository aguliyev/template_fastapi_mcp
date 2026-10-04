from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from template_fastapi_mcp.greetings import GreetingService, StorageUnavailable
from template_fastapi_mcp.schemas import (
    GreetingCreate,
    GreetingList,
    GreetingOut,
    Limit,
    Name,
)


def build_mcp(service: GreetingService) -> MCPServer:
    server = MCPServer("Greeting template")

    @server.tool(structured_output=True)
    async def create_greeting(name: Name) -> GreetingOut:
        """Store a greeting and return its identifier, name, and UTC creation time."""
        try:
            return await service.create(GreetingCreate(name=name))
        except StorageUnavailable:
            raise ToolError("Greeting storage is unavailable") from None

    @server.tool(structured_output=True)
    async def list_greetings(limit: Limit = 20) -> GreetingList:
        """Return up to 100 greetings, ordered newest first."""
        try:
            return GreetingList(greetings=await service.list(limit))
        except StorageUnavailable:
            raise ToolError("Greeting storage is unavailable") from None

    return server
