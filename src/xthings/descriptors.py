from __future__ import annotations
from abc import ABC, abstractmethod
import anyio
import anyio.from_thread
from fastapi import Body, FastAPI, Request, BackgroundTasks
from functools import partial
from pydantic import BaseModel
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
from typing_extensions import Self
import uuid

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
    model: type[BaseModel]
    readonly: bool

    def __init__(
        self,
        model: type,
        initial_value: Any = None,
        getter: Optional[Callable] = None,
        setter: Optional[Callable] = None,
    ):
        self.model = model
        self._value = initial_value
        self._getter = getter or getattr(self, "_getter", None)
        self._setter = setter or getattr(self, "_setter", None)

    def __set_name__(self, owner, name: str):
        self._name = name

    def __get__(self, obj, type=None) -> Any:
        if obj is None:
            return self

        if self._getter:
            return self._getter(obj)

        return self._value

    def __set__(self, obj, value):
        self._value = value
        if self._setter:
            self._setter(obj, value)

        self.emit_changed_event(obj, value)

    def emit_changed_event(self, xthing: XThing, value: Any):
        try:
            anyio.from_thread.run(self.emit_changed_event_async, xthing, value)
        except Exception as e:
            return e

    async def emit_changed_event_async(self, xthing: XThing, value: Any):
        try:
            for observer in xthing.observers(self.name):
                await observer.send(
                    {"messageType": "propertyStatus", "data": {self.name: value}}
                )
        except Exception as e:
            print("error", str(e))

    @property
    def name(self):
        return self._name

    def add_to_app(self, app: FastAPI, xthing: XThing):
        def set_property(body):
            return self.__set__(xthing, body)

        set_property.__annotations__["body"] = Annotated[self.model, Body()]
        app.put(pathjoin(xthing.path, self.name), status_code=200)(set_property)

        @app.get(pathjoin(xthing.path, self.name), response_model=self.model)
        def get_property():
            return self.__get__(xthing)

    def property_affordance(self, xthing: XThing, path: Optional[str] = None): ...

    def setter(self, func: Callable) -> Self:
        self._setter = func
        return self


class ActionDescriptor(XThingsDescriptor):
    def __init__(
        self,
        func: Callable,
        input_model: BaseModel = None,
        output_model: BaseModel = None,
    ):
        self._func = func
        self._input_model = input_model
        self._output_model = output_model

    def __set_name__(self, owner, name: str):
        self._name = name

    @overload
    def __get__(self, xthing_obj: Literal[None], type=None) -> ActionDescriptor: ...

    @overload
    def __get__(self, xthing_obj: XThing, type=None) -> Callable: ...

    def __get__(
        self, xthing_obj: Optional[XThing], type=None
    ) -> Union[ActionDescriptor, Callable]:
        """The function"""
        if xthing_obj is None:
            return self

        return partial(self._func, xthing_obj)

    @property
    def name(self):
        return self._name

    @property
    def input_model(self):
        return self._input_model

    @property
    def output_model(self):
        return self._output_model

    def add_to_app(self, app: FastAPI, xthing: XThing):
        async def start_action(
            request: Request, body, background_tasks: BackgroundTasks
        ):
            action = xthing._action_manager.invoke_action(
                action=self, xthing=xthing, input=body, id=uuid.uuid4()
            )

            return action.response(request=request)

        start_action.__annotations__["body"] = Annotated[self.input_model, Body()]
        app.post(pathjoin(xthing.path, self.name), status_code=201)(start_action)

        async def list_invocations():
            return []

        app.get(pathjoin(xthing.path, self.name))(list_invocations)
