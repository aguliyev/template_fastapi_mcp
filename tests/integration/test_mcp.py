import httpx
import pytest
from mcp import Client


@pytest.mark.anyio
@pytest.mark.integration
@pytest.mark.parametrize("mode", ["auto", "legacy"])
async def test_mcp_tool_round_trip(live_url, mode):
    async with Client(live_url + "/mcp", mode=mode) as client:
        tools = await client.list_tools()
        assert {tool.name for tool in tools.tools} == {
            "create_greeting",
            "list_greetings",
        }
        created = await client.call_tool("create_greeting", {"name": "  Anar  "})
        assert not created.is_error
        assert created.structured_content["name"] == "Anar"
        listed = await client.call_tool("list_greetings", {"limit": 1})
        assert listed.structured_content["greetings"][0] == created.structured_content
        if mode == "auto":
            assert client.protocol_version == "2026-07-28"
        else:
            assert client.protocol_version == "2025-11-25"


@pytest.mark.anyio
@pytest.mark.integration
async def test_exact_mcp_route_does_not_redirect(live_url):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "route-test", "version": "1"},
        },
    }
    async with httpx.AsyncClient(follow_redirects=False) as http:
        response = await http.post(
            live_url + "/mcp",
            json=payload,
            headers={"Accept": "application/json, text/event-stream"},
        )
        assert response.status_code == 200
        assert "location" not in response.headers
        assert response.json()["result"]["protocolVersion"] == "2025-11-25"


@pytest.mark.anyio
@pytest.mark.integration
async def test_mcp_host_allowlist(live_url, test_settings):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "route-test", "version": "1"},
        },
    }
    headers = {"Accept": "application/json, text/event-stream"}
    async with httpx.AsyncClient(
        base_url=live_url, follow_redirects=False
    ) as http:
        rejected = await http.post(
            "/mcp", json=payload, headers={**headers, "Host": "untrusted.example"}
        )
        assert rejected.status_code == 421
        for host in [
            "localhost",
            f"127.0.0.1:{test_settings.test_http_port}",
            "app:8000",
        ]:
            response = await http.post(
                "/mcp", json=payload, headers={**headers, "Host": host}
            )
            assert response.status_code == 200
            assert "result" in response.json()


@pytest.mark.anyio
@pytest.mark.integration
async def test_mcp_tool_schemas(live_url):
    async with Client(live_url + "/mcp") as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}
        create = tools["create_greeting"]
        assert create.input_schema["type"] == "object"
        assert create.input_schema["properties"]["name"]["maxLength"] == 100
        assert create.output_schema["type"] == "object"
        assert set(create.output_schema["properties"]) == {"id", "name", "created_at"}
        listing = tools["list_greetings"]
        assert listing.input_schema["type"] == "object"
        assert listing.input_schema["properties"]["limit"]["minimum"] == 1
        assert listing.input_schema["properties"]["limit"]["maximum"] == 100
        assert listing.input_schema["properties"]["limit"]["default"] == 20
        assert listing.output_schema["type"] == "object"
        assert set(listing.output_schema["properties"]) == {"greetings"}
        assert (
            listing.output_schema["properties"]["greetings"]["type"] == "array"
        )


@pytest.mark.anyio
@pytest.mark.integration
async def test_mcp_validation_boundaries(live_url):
    async with Client(live_url + "/mcp") as client:
        assert (await client.call_tool("create_greeting", {"name": "   "})).is_error
        assert (
            await client.call_tool("create_greeting", {"name": "a" * 101})
        ).is_error
        assert (await client.call_tool("list_greetings", {"limit": 0})).is_error
        assert (await client.call_tool("list_greetings", {"limit": 101})).is_error
        for limit in (1, 100):
            result = await client.call_tool("list_greetings", {"limit": limit})
            assert not result.is_error
            assert result.structured_content == {"greetings": []}
