from __future__ import annotations
from abc import ABC, abstractmethod
from fastapi import Body, FastAPI, Request, BackgroundTasks
from functools import partial
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Optional,
    Callable,
    Literal,
    Union,
    overload,
)


if TYPE_CHECKING:  # pragma: no cover
    from .xthing import XThing


def pathjoin(pa, pb):
    while pa.endswith("/"):
        pa = pa[:-1]

    while pb.startswith("/"):
        pb = pb[1:]

    return pa + "/" + pb


class XThingsDescriptor(ABC):
    @classmethod
    def get_xdescriptors(cls, obj: XThing):
        objcls = obj.__class__
        for name in dir(objcls):
            if name.startswith("__"):
                continue
            attr = getattr(objcls, name)
            if isinstance(attr, XThingsDescriptor):
                yield attr

    @abstractmethod
    def add_to_app(self, app: FastAPI, xthing: XThing): ...


class PropertyDescriptor(XThingsDescriptor):
    _value: Any

    def __init__(self, initial_value: Any = None):
        self._value = initial_value

    def __set_name__(self, owner, name: str):
        self._name = name

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        return self._value

    def __set__(self, obj, value):
        self._value = value
        return self._value

    @property
    def name(self):
        return self._name

    def add_to_app(self, app: FastAPI, xthing: XThing):
        async def set_property(body):
            return self.__set__(xthing, body)

        set_property.__annotations__["body"] = Annotated[int, Body()]
        app.put(pathjoin(xthing.path, self.name), status_code=200)(set_property)

        @app.get(pathjoin(xthing.path, self.name))
        async def get_property():
            return self.__get__(xthing)

    def property_affordance(self, xthing: XThing, path: Optional[str] = None): ...


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
