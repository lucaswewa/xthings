"""
Define an object to represent an XProperty, as a Python descriptor
"""

from __future__ import annotations
from fastapi import Body, FastAPI, Request, BackgroundTasks
from functools import partial
from typing import (
    TYPE_CHECKING,
    Annotated,
    Optional,
    Callable,
    Literal,
    Union,
    overload,
)

from xthings.xthing import XThing

from .descriptors import XThingsDescriptor

if TYPE_CHECKING:  # pragma: no cover
    from .xthing import XThing


def pathjoin(pa, pb):
    while pa.endswith("/"):
        pa = pa[:-1]

    while pb.startswith("/"):
        pb = pb[1:]

    return pa + "/" + pb


class ActionDescriptor(XThingsDescriptor):
    def __init__(self, func: Callable):
        self._func = func

    def __set_name__(self, owner, name: str):
        self._name = name

    @overload
    def __get__(self, obj: Literal[None], type=None) -> ActionDescriptor: ...

    @overload
    def __get__(self, obj: XThing, type=None) -> Callable: ...

    def __get__(
        self, obj: Optional[XThing], type=None
    ) -> Union[ActionDescriptor, Callable]:
        if obj is None:
            return self

        return partial(self._func, obj)

    @property
    def name(self):
        return self._name

    def add_to_app(self, app: FastAPI, xthing: XThing):
        async def start_action(
            request: Request, body, background_tasks: BackgroundTasks
        ):
            background_tasks.add_task(partial(self._func, xthing), body)
            return 201

        start_action.__annotations__["body"] = Annotated[int, Body()]

        app.post(pathjoin(xthing.path, self.name), status_code=201)(start_action)

        async def list_invocations():
            return []

        app.get(pathjoin(xthing.path, self.name))(list_invocations)
