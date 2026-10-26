from fastapi.testclient import TestClient

from python_template.routes.hello import greet


def test_greet() -> None:
    assert greet("Ada") == "Hello, Ada!"


def test_greets_the_world_by_default(client: TestClient) -> None:
    res = client.get("/v1/hello")
    assert res.status_code == 200
    assert res.json() == {"message": "Hello, world!"}


def test_greets_the_given_name(client: TestClient) -> None:
    assert client.get("/v1/hello", params={"name": "Ada"}).json() == {"message": "Hello, Ada!"}


def test_rejects_a_name_that_is_too_long(client: TestClient) -> None:
    assert client.get("/v1/hello", params={"name": "a" * 101}).status_code == 422
