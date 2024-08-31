from __future__ import annotations
import anyio
import anyio.from_thread
from fastapi import Body, FastAPI
from pydantic import BaseModel
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Optional,
    Callable,
)
from typing_extensions import Self
import uuid

from ..utils import pathjoin
from .xthings import XThingsDescriptor

if TYPE_CHECKING:  # pragma: no cover
    from ..xthing import XThing


class LcrudDescriptor(XThingsDescriptor):
    _model: type[BaseModel]
    _readonly: bool

    def __init__(
        self,
        item_model: type,
        list_func: Callable,
        create_func: Optional[Callable] = None,
        retrieve_func: Optional[Callable] = None,
        update_func: Optional[Callable] = None,
        delete_func: Optional[Callable] = None,
    ):
        self._model = item_model
        self._list_func: Callable = list_func
        self._create_func: Optional[Callable] = create_func or getattr(
            self, "_create_func", None
        )
        self._retrieve_func: Optional[Callable] = retrieve_func or getattr(
            self, "_retrieve_func", None
        )
        self._update_func: Optional[Callable] = update_func or getattr(
            self, "_update_func", None
        )
        self._delete_func: Optional[Callable] = delete_func or getattr(
            self, "_delete_func", None
        )

    def __set_name__(self, owner, name: str):
        self._name = name

    def __get__(self, obj, type=None) -> Any:
        if obj is None:
            return self
        else:
            # The getter is running in an anyio worker thread
            return self._list_func(obj)

    @property
    def name(self):
        return self._name

    def create_func(self, func: Callable) -> Self:
        self._create_func = func
        return self

    def retrieve_func(self, func: Callable) -> Self:
        self._retrieve_func = func
        return self

    def update_func(self, func: Callable) -> Self:
        self._update_func = func
        return self

    def delete_func(self, func: Callable) -> Self:
        self._delete_func = func
        return self

    def add_to_app(self, app: FastAPI, xthing: XThing):
        def get_collection():
            return self.__get__(xthing)

        app.get(pathjoin(xthing.path, self.name))(get_collection)

        if self._create_func is not None:
            create_func = self._create_func

            def create_item(body):
                return create_func(xthing, body)

            create_item.__annotations__["body"] = Annotated[self._model, Body()]
            app.post(pathjoin(xthing.path, self.name))(create_item)

        if self._retrieve_func is not None:
            retrieve_func = self._retrieve_func

            def retrieve_item(id: uuid.UUID):
                return retrieve_func(xthing, id)

            app.get(pathjoin(xthing.path, self.name) + "/{id}")(retrieve_item)

        if self._update_func is not None:
            update_func = self._update_func

            def update_item(id: uuid.UUID, body):
                return update_func(xthing, id, body)

            update_item.__annotations__["body"] = Annotated[self._model, Body()]
            app.put(pathjoin(xthing.path, self.name) + "/{id}")(update_item)

        if self._delete_func is not None:
            del_func = self._delete_func

            def delete_item(id: uuid.UUID):
                return del_func(xthing, id)

            app.delete(pathjoin(xthing.path, self.name) + "/{id}")(delete_item)


class PropertyDescriptor(XThingsDescriptor):
    _value: Any
    _model: type[BaseModel]
    _readonly: bool

    def __init__(
        self,
        model: type,
        initial_value: Any = None,
        getter: Optional[Callable] = None,
        setter: Optional[Callable] = None,
    ):
        self._model = model
        self._value = initial_value
        self._getter = getter or getattr(self, "_getter", None)
        self._setter = setter or getattr(self, "_setter", None)
        self._readonly = False

    def __set_name__(self, owner, name: str):
        self._name = name

    def __get__(self, obj, type=None) -> Any:
        if obj is None:
            return self

        # The getter is running in an anyio worker thread
        if self._getter:
            return self._getter(obj)

        return self._value

    def __set__(self, obj, value):
        self._value = value
        # The setter is running in an anyio worker thread
        if self._setter:
            self._setter(obj, value)

        self.emit_changed_event(obj, value)

    def emit_changed_event(self, xthing: XThing, value: Any):
        try:
            anyio.from_thread.run(self._emit_changed_event_async, xthing, value)
        except Exception as e:
            return e

    async def _emit_changed_event_async(self, xthing: XThing, value: Any):
        try:
            for observer in xthing.property_observers(self.name):
                await observer.send(
                    {"messageType": "propertyStatus", "data": {self.name: value}}
                )
        except Exception:
            # TODO: handle exception
            ...

    @property
    def name(self):
        return self._name

    def add_to_app(self, app: FastAPI, xthing: XThing):
        def set_property(body):
            return self.__set__(xthing, body)

        set_property.__annotations__["body"] = Annotated[self._model, Body()]
        app.put(pathjoin(xthing.path, self.name), status_code=200)(set_property)

        @app.get(pathjoin(xthing.path, self.name), response_model=self._model)
        def get_property():
            return self.__get__(xthing)

    def setter(self, func: Callable) -> Self:
        self._setter = func
        return self

    def description(self) -> Any:
        return {}
