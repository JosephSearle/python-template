from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from python_template import health
from python_template.health import ReadinessRegistry
from python_template.log import RequestLogMiddleware
from python_template.routes import hello


def create_app(registry: ReadinessRegistry | None = None) -> FastAPI:
    """Builds the app. Tests pass their own registry to register checks."""
    readiness = registry or ReadinessRegistry()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        # Connect to dependencies here and register their readiness checks, e.g.
        # readiness.register("database", database.ping)
        yield
        # Close connections here. Readiness is already failing by the time this runs.

    app = FastAPI(title="python-template", lifespan=lifespan)
    app.state.readiness = readiness
    app.add_middleware(RequestLogMiddleware)
    app.include_router(health.router)
    app.include_router(hello.router)
    return app
