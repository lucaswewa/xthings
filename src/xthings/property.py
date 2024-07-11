"""
Define an object to represent an XProperty, as a Python descriptor
"""

from __future__ import annotations
from fastapi import Body, FastAPI
from typing import TYPE_CHECKING, Annotated, Any, Optional

from .descriptors import XThingsDescriptor

if TYPE_CHECKING:  # pragma: no cover
    from .xthing import XThing


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
        def pathjoin(pa, pb):
            while pa.endswith("/"):
                pa = pa[:-1]

            while pb.startswith("/"):
                pb = pb[1:]

            return pa + "/" + pb

        async def set_property(body):
            return self.__set__(xthing, body)

        set_property.__annotations__["body"] = Annotated[int, Body()]
        app.put(pathjoin(xthing.path, self.name), status_code=200)(set_property)

        @app.get(pathjoin(xthing.path, self.name))
        async def get_property():
            return self.__get__(xthing)

    def property_affordance(self, xthing: XThing, path: Optional[str] = None): ...
