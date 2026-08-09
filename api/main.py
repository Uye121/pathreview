from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import redis
import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from api.middleware.rate_limit import RateLimitMiddleware
from api.middleware.request_id import RequestIDMiddleware
from api.routes import auth, health, profiles, reviews
from core.config import settings
from core.database import init_db

log = structlog.get_logger()
# Initialize redis client
redis_client = redis.Redis.from_url(settings.redis_url)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup event
    # Store reference to redis for other parts of the application to use
    app.state.redis = redis_client
    await init_db()
    log.info("application_startup_completed")

    yield

    # Shutdown event
    redis_client.close()
    log.info("application_shutdown_completed")


# Create FastAPI application
app = FastAPI(
    title="PathReview API",
    lifespan=lifespan,
    description="AI-powered portfolio review assistant",
    version="1.0.0",
)


# Configure OpenAPI
def custom_openapi() -> dict[str, Any]:
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="PathReview API",
        version="1.0.0",
        description="AI-powered portfolio review assistant",
        routes=app.routes,
    )

    openapi_schema["info"]["x-logo"] = {"url": "https://pathreview.example.com/logo.png"}

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware ordering note: Starlette runs middleware in reverse order of
# registration, so the LAST one added is the OUTERMOST (runs first on the way
# in). RequestIDMiddleware is registered after RateLimitMiddleware on purpose,
# so it wraps rate limiting and binds request_id first — that way a 429 from the
# rate limiter is still logged with its request_id. Keep this order.

# Add per-IP + per-user rate limiting middleware (runs for public and
# authenticated routes). trust_proxy stays off until a known proxy fronts the
# API, otherwise clients could spoof X-Forwarded-For to dodge the limit.
app.add_middleware(
    RateLimitMiddleware,
    redis_client=redis_client,
    limit=settings.rate_limit_per_minute,
)

# Add request ID middleware (outermost — see ordering note above)
app.add_middleware(RequestIDMiddleware)


# Exception handler for unhandled exceptions
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    log.error(
        "unhandled_exception",
        request_id=request_id,
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "request_id": request_id,
        },
    )


# Include routers
app.include_router(auth.router)
app.include_router(profiles.router)
app.include_router(reviews.router)
app.include_router(health.router)


# Root endpoint
@app.get("/")
async def root() -> dict[str, str]:
    """Health check endpoint."""
    return {
        "message": "PathReview API is running",
        "version": "1.0.0",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
