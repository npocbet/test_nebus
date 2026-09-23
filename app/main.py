from fastapi import Depends, FastAPI

from app.api.v1.router import router as api_v1_router
from app.security import require_api_key


app = FastAPI(
    title="Payment Service",
    version="1.0.0",
    dependencies=[Depends(require_api_key)],
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.include_router(api_v1_router)


@app.get("/health", tags=["system"])
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
