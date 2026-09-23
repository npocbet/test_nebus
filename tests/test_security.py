import pytest
from fastapi import HTTPException

from app import security


@pytest.mark.asyncio
async def test_api_key_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(security, "API_KEY", "secret")
    with pytest.raises(HTTPException) as error:
        await security.require_api_key(None)
    assert error.value.status_code == 401


@pytest.mark.asyncio
async def test_valid_api_key_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(security, "API_KEY", "secret")
    assert await security.require_api_key("secret") is None
