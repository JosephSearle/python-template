"""Example resource. Replace it with your own routers; keep the validate-then-delegate shape."""

from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter(prefix="/v1/hello", tags=["hello"])


class Greeting(BaseModel):
    message: str


def greet(name: str) -> str:
    return f"Hello, {name}!"


@router.get("")
def get_hello(
    name: Annotated[str, Query(min_length=1, max_length=100)] = "world",
) -> Greeting:
    return Greeting(message=greet(name.strip() or "world"))
