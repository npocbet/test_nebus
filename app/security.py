import os
import secrets
from typing import Annotated

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader


API_KEY = os.getenv("API_KEY", "dev-api-key")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(
    provided_api_key: Annotated[str | None, Security(api_key_header)],
) -> None:
    if provided_api_key is None or not secrets.compare_digest(
        provided_api_key,
        API_KEY,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
