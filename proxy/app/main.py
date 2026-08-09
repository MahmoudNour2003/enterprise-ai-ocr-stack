"""FastAPI Application Main Entrypoint."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from app.client import iti_client
from app.converter import format_openai_error
from app.routes import router
from app.settings import settings
from app.utils import logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan manager for HTTP client lifecycle."""
    logger.info("Initializing ITI HTTP Client...")
    await iti_client.start()
    yield
    logger.info("Closing ITI HTTP Client...")
    await iti_client.close()


app = FastAPI(
    title="Enterprise AI Provider -> OpenAI Compatibility Server",
    description="FastAPI service enabling OpenAI-compatible client access to ITI Enterprise AI Provider.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom exception handler to return OpenAI-style error format."""
    error_payload = format_openai_error(
        message=str(exc.detail),
        error_type="api_error" if exc.status_code >= 500 else "invalid_request_error",
        code=str(exc.status_code),
    )
    return JSONResponse(status_code=exc.status_code, content=error_payload)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Global unhandled exception handler."""
    logger.error(f"Unhandled server error: {exc}", exc_info=True)
    error_payload = format_openai_error(
        message="An internal server error occurred.",
        error_type="server_error",
        code="500",
    )
    return JSONResponse(status_code=500, content=error_payload)


app.include_router(router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=True,
    )
