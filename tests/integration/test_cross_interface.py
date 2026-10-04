import pytest
from httpx import AsyncClient
from mcp import Client


@pytest.mark.anyio
@pytest.mark.integration
async def test_rest_and_mcp_share_persistence(live_url):
    async with AsyncClient(base_url=live_url, timeout=5) as rest:
        async with Client(live_url + "/mcp") as mcp:
            created_rest = await rest.post("/greetings", json={"name": "Rest Name"})
            assert created_rest.status_code == 201
            rest_greeting = created_rest.json()
            listed_by_mcp = await mcp.call_tool("list_greetings", {"limit": 10})
            assert not listed_by_mcp.is_error
            assert listed_by_mcp.structured_content["greetings"][0] == rest_greeting

            created_mcp = await mcp.call_tool("create_greeting", {"name": "MCP Name"})
            assert not created_mcp.is_error
            mcp_greeting = created_mcp.structured_content
            listed_by_rest = await rest.get("/greetings", params={"limit": 10})
            assert listed_by_rest.status_code == 200
            assert listed_by_rest.json()[0] == mcp_greeting
            assert listed_by_rest.json()[1] == rest_greeting
