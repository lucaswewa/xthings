from __future__ import annotations
from abc import ABC, abstractmethod
from fastapi import FastAPI

from typing import (
    TYPE_CHECKING,
)

if TYPE_CHECKING:  # pragma: no cover
    from ..xthing import XThing


class XThingsDescriptor(ABC):
    @classmethod
    def get_xdescriptors(cls, obj: XThing):
        objcls = obj.__class__
        for name in dir(objcls):
            if name.startswith("__"):
                continue
            attr = getattr(objcls, name)
            if isinstance(attr, XThingsDescriptor):
                yield name, attr

    @abstractmethod
    def add_to_app(self, app: FastAPI, xthing: XThing): ...
