"""Liveness and readiness probes.

Register a check for each dependency the service can't serve without, e.g. in the app lifespan:

    registry.register("database", database.ping)
"""

import asyncio
import inspect
import logging
from collections.abc import Awaitable, Callable
from typing import Literal

from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Returns (or resolves) when the dependency is usable, raises when it isn't.
ReadinessCheck = Callable[[], Awaitable[None] | None]
CheckStatus = Literal["ok", "error", "timeout"]

CHECK_TIMEOUT_SECONDS = 2.0


class LivenessReport(BaseModel):
    status: Literal["ok"] = "ok"


class ReadinessReport(BaseModel):
    status: Literal["ok", "unavailable"]
    checks: dict[str, CheckStatus]


class ReadinessRegistry:
    def __init__(self) -> None:
        self._checks: dict[str, ReadinessCheck] = {}
        self._draining = False

    def register(self, name: str, check: ReadinessCheck) -> None:
        if name in self._checks:
            raise ValueError(f'Readiness check "{name}" is already registered.')
        self._checks[name] = check

    def start_draining(self) -> None:
        """Fails readiness from now on, so the platform stops routing here before shutdown."""
        self._draining = True

    @property
    def draining(self) -> bool:
        return self._draining

    async def report(self) -> ReadinessReport:
        names = list(self._checks)
        results = await asyncio.gather(*(self._run(n, self._checks[n]) for n in names))
        checks = dict(zip(names, results, strict=True))
        healthy = not self._draining and all(s == "ok" for s in results)
        return ReadinessReport(status="ok" if healthy else "unavailable", checks=checks)

    async def _run(self, name: str, check: ReadinessCheck) -> CheckStatus:
        async def call() -> None:
            if inspect.iscoroutinefunction(check):
                await check()
            else:
                # Sync checks run in a thread so a slow one can't block the event loop.
                result = await asyncio.to_thread(check)
                if inspect.isawaitable(result):
                    await result

        try:
            await asyncio.wait_for(call(), timeout=CHECK_TIMEOUT_SECONDS)
        except TimeoutError:
            logger.warning('Readiness check "%s" timed out', name)
            return "timeout"
        except Exception:
            # Logged, not returned: error messages can name internal hosts.
            logger.warning('Readiness check "%s" failed', name, exc_info=True)
            return "error"
        return "ok"


router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz() -> LivenessReport:
    """Liveness: the process is up. Never checks dependencies, so a slow database can't get the
    container restarted."""
    return LivenessReport()


@router.get(
    "/readyz",
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadinessReport}},
)
async def readyz(request: Request, response: Response) -> ReadinessReport:
    """Readiness: every registered check passed and the service isn't shutting down."""
    registry: ReadinessRegistry = request.app.state.readiness
    report = await registry.report()
    if report.status != "ok":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return report
