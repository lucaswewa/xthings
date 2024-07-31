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
from .descriptors import (
    XThingsDescriptor,
    ActionDescriptor,
    PropertyDescriptor,
    ImageStreamDescriptor,
)

if TYPE_CHECKING:  # pragma: no cover
    from .server import XThingsServer


class XThing:
    _path: str
    _properties: dict[str, Any] = {}
    _actions: dict[str, Any] = {}
    _streams: dict[str, Any] = {}
    _components: dict[str, Any] = {}
    _blocking_portal: Optional[BlockingPortal] = None
    _observers: dict[str, WeakSet[ObjectSendStream]] = {}
    _property_observers: dict[str, WeakSet[ObjectSendStream]] = {}
    _action_observers: dict[str, WeakSet[ObjectSendStream]] = {}
    _settings: dict = {}
    _ut_probe: Any

    def __init__(self, service_type, service_name):
        self._service_type = service_type
        self._service_name = service_name

    async def __aenter__(self):
        """Asynchronous Context management is used to setup the XThing"""
        return await run_sync(self.setup)

    async def __aexit__(self, exc_t, exc_v, exc_tb):
        """Asynchronous Context management is used to shutdown the XThing"""
        return await run_sync(self.teardown)

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
        """Associate components (objects) with this XThing object"""
        self._components[name] = component

    def find_component(self, name: str):
        """Get the components by name"""
        return self._components[name]

    def attach_to_app(self, server: XThingsServer, path: str):
        """Add HTTP handlers to the app for this XThing"""
        self._path = path
        self._action_manager = server.action_manager

        for name, xdescriptor in XThingsDescriptor.get_xthings_descriptors(self):
            if isinstance(xdescriptor, PropertyDescriptor):
                self._properties[name] = xdescriptor
            elif isinstance(xdescriptor, ActionDescriptor):
                self._actions[name] = xdescriptor
            elif isinstance(xdescriptor, ImageStreamDescriptor):
                self._streams[name] = xdescriptor
            else:
                pass
            xdescriptor.add_to_app(server.app, self)

        # register XThing description endpoint
        def get_TD(request: Request):
            return self.description(base=str(request.base_url))

        server.app.get(
            self.path, response_model_exclude_none=True, response_model_by_alias=True
        )(get_TD)

        # register XThing websocket endpoint
        async def websocket(ws: WebSocket):
            await websocket_endpoint(self, ws)

        server.app.websocket(self.path + "/ws")(websocket)

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

    def description(self, path: Optional[str] = None, base: Optional[str] = None):
        return {
            "properties": {
                key: item.description() for (key, item) in self._properties.items()
            },
            "actions": {
                key: item.description() for (key, item) in self._actions.items()
            },
            "streams": {
                key: item.description() for (key, item) in self._streams.items()
            },
        }
