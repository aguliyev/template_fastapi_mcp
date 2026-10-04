import pytest


@pytest.mark.anyio
@pytest.mark.integration
async def test_rest_creation_and_listing(rest_client):
    created = await rest_client.post("/greetings", json={"name": "  Anar  "})
    assert created.status_code == 201
    greeting = created.json()
    assert greeting["name"] == "Anar"
    assert greeting["created_at"].endswith("Z")
    listed = await rest_client.get("/greetings", params={"limit": 1})
    assert listed.status_code == 200
    assert listed.json() == [greeting]


@pytest.mark.anyio
@pytest.mark.integration
@pytest.mark.parametrize(
    "payload",
    [
        {"name": "   "},
        {"name": "a" * 101},
        {},
        {"name": "Anar", "extra": "field"},
    ],
)
async def test_rest_create_rejects_invalid_names(rest_client, payload):
    response = await rest_client.post("/greetings", json=payload)
    assert response.status_code == 422


@pytest.mark.anyio
@pytest.mark.integration
@pytest.mark.parametrize("limit", [0, 101, "abc"])
async def test_rest_list_rejects_invalid_limits(rest_client, limit):
    response = await rest_client.get("/greetings", params={"limit": limit})
    assert response.status_code == 422


@pytest.mark.anyio
@pytest.mark.integration
async def test_rest_docs_remain_accessible(rest_client):
    docs = await rest_client.get("/docs")
    assert docs.status_code == 200
    schema = await rest_client.get("/openapi.json")
    assert schema.status_code == 200
    paths = schema.json()["paths"]
    assert "/greetings" in paths
    assert "/health" in paths
