"""
The XThing class
"""

from __future__ import annotations
from anyio.to_thread import run_sync
from anyio.from_thread import BlockingPortal
from anyio.abc import ObjectSendStream
from fastapi import Request
from typing import Any, TYPE_CHECKING, Optional
from weakref import WeakSet

from .server import websocket_endpoint, WebSocket
from .descriptors import XThingsDescriptor

if TYPE_CHECKING:  # pragma: no cover
    from .server import XThingsServer


class XThing:
    _path: str
    _components: dict[str, Any] = {}
    _xthings_blocking_portal: Optional[BlockingPortal] = None
    _observers: dict[str, WeakSet[ObjectSendStream]] = {}
    _property_observers: dict[str, WeakSet[ObjectSendStream]] = {}
    _action_observers: dict[str, WeakSet[ObjectSendStream]] = {}
    _settings: dict = {}
    _ut_probe: Any

    def __init__(self, service_type, service_name):
        self._service_type = service_type
        self._service_name = service_name

    async def __aenter__(self):
        """Context management is used to setup the XThing"""
        return await run_sync(self.__enter__)

    async def __aexit__(self, exc_t, exc_v, exc_tb):
        """Context management is used to shutdown the XThing"""
        return await run_sync(self.__exit__, exc_t, exc_v, exc_tb)

    def __enter__(self):
        self.setup()
        return self

    def __exit__(self, *args):
        self.teardown()

    @property
    def path(self):
        return self._path

    @property
    def settings(self):
        return self._settings

    @settings.setter  # type: ignore[no-redef]
    def settings(self, val):
        self._settings = val

    @property
    def action_manager(self):
        return self._action_manager

    def setup(self):
        """Setup the XThing hardware or other initialization operations

        Subclass should override this method.
        """
        self._ut_probe = "setup"

    def teardown(self):
        """Shutdown the XThing hardware or other deinitialization operations

        Subclass should override this method.
        """
        self._ut_probe = "shutdown"

    def add_component(self, component, name):
        self._components[name] = component

    def find_component(self, name: str):
        return self._components[name]

    def attach_to_app(self, server: XThingsServer, path: str):
        """Add HTTP handlers to the app for this XThing"""
        self._path = path
        self._action_manager = server.action_manager

        for name, xdescriptor in XThingsDescriptor.get_xdescriptors(self):
            xdescriptor.add_to_app(server.app, self)

        @server.app.get(
            self.path, response_model_exclude_none=True, response_model_by_alias=True
        )
        def thing_description(request: Request):
            return self.thing_description(base=str(request.base_url))

        @server.app.websocket(self.path + "/ws")
        async def websocket(ws: WebSocket):
            await websocket_endpoint(self, ws)

    def property_observers(self, attr: str) -> WeakSet[ObjectSendStream[Any]]:
        if attr not in self._property_observers.keys():
            self._property_observers[attr] = WeakSet()
        return self._property_observers[attr]

    def action_observers(self, attr: str) -> WeakSet[ObjectSendStream[Any]]:
        if attr not in self._action_observers.keys():
            self._action_observers[attr] = WeakSet()
        return self._action_observers[attr]

    def add_property_observer_by_attr(
        self, attr: str, observer_stream: ObjectSendStream
    ) -> None:
        self.property_observers(attr).add(observer_stream)

    def add_action_observer_by_attr(
        self, attr: str, observer_stream: ObjectSendStream
    ) -> None:
        self.action_observers(attr).add(observer_stream)

    def remove_property_observer_by_attr(
        self, attr: str, observer_stream: ObjectSendStream
    ) -> None:
        self.property_observers(attr).remove(observer_stream)

    def remove_action_observer_by_attr(
        self, attr: str, observer_stream: ObjectSendStream
    ) -> None:
        self.action_observers(attr).remove(observer_stream)

    def thing_description(self, path: Optional[str] = None, base: Optional[str] = None):
        path = path or getattr(self, "path", "{base_uri}")
        properties = {}
        actions = {}

        for name, item in XThingsDescriptor.get_xdescriptors(self):
            if hasattr(item, "property_description"):
                properties[name] = item.property_description(self, path)
            if hasattr(item, "action_description"):
                actions[name] = item.action_description(self, path)

        return {
            "title": getattr(self, "title", self.__class__.__name__),
            "properties": properties,
            "actions": actions,
        }
