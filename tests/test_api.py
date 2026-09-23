import httpx
import pytest

from app.main import app


@pytest.fixture
def transport() -> httpx.ASGITransport:
    return httpx.ASGITransport(app=app)


@pytest.mark.asyncio
async def test_payment_endpoint_requires_api_key(transport: httpx.ASGITransport) -> None:
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/payments/00000000-0000-0000-0000-000000000000"
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_health_endpoint_requires_api_key(transport: httpx.ASGITransport) -> None:
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_interactive_docs_are_not_exposed(transport: httpx.ASGITransport) -> None:
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        assert (await client.get("/docs")).status_code == 404
        assert (await client.get("/openapi.json")).status_code == 404
