from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from python_template.app import create_app
from python_template.health import ReadinessRegistry


@pytest.fixture
def registry() -> ReadinessRegistry:
    return ReadinessRegistry()


@pytest.fixture
def client(registry: ReadinessRegistry) -> Iterator[TestClient]:
    with TestClient(create_app(registry)) as client:
        yield client
