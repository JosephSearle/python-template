"""Starts the server: python -m python_template"""

import asyncio
import logging
from types import FrameType
from typing import override

import uvicorn

from python_template.app import create_app
from python_template.health import ReadinessRegistry
from python_template.log import configure_logging
from python_template.settings import load_settings

logger = logging.getLogger("python_template.server")


class DrainingServer(uvicorn.Server):
    """On the first SIGTERM or SIGINT, fails /readyz and keeps serving for the drain period, so the
    platform stops routing here before uvicorn stops accepting connections. A second signal stops
    at once."""

    def __init__(self, config: uvicorn.Config, registry: ReadinessRegistry, drain_ms: int) -> None:
        super().__init__(config)
        self.registry = registry
        self.drain_seconds = drain_ms / 1000

    @override
    def handle_exit(self, sig: int, frame: FrameType | None) -> None:
        if self.drain_seconds == 0 or self.registry.draining:
            super().handle_exit(sig, frame)
            return
        self.registry.start_draining()
        logger.info("Draining for %d ms before shutdown", self.drain_seconds * 1000)
        loop = asyncio.get_event_loop()
        # Thread-safe call wakes the loop; the signal handler may run while it waits on I/O.
        loop.call_soon_threadsafe(
            loop.call_later, self.drain_seconds, super().handle_exit, sig, frame
        )


def main() -> None:
    settings = load_settings()
    configure_logging(settings.log_level)
    registry = ReadinessRegistry()
    config = uvicorn.Config(
        create_app(registry),
        host="0.0.0.0",
        port=settings.port,
        log_config=None,
        access_log=False,
        proxy_headers=True,
        # Container Apps' ingress is the only client that reaches the container.
        forwarded_allow_ips="*",
    )
    DrainingServer(config, registry, settings.shutdown_drain_ms).run()


if __name__ == "__main__":
    main()
