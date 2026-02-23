"""FastAPI application entrypoint."""

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import get_settings

settings = get_settings()
app = FastAPI(title=settings.APP_NAME)
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/healthz")
async def healthcheck() -> dict[str, str]:
    """Return service health status.

    Args:
        None
    Returns:
        dict[str, str]: Health status payload.
    """
    return {"status": "ok"}
