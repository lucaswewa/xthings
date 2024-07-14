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
from .websocket import websocket_endpoint, WebSocket
from .descriptors import XThingsDescriptor

if TYPE_CHECKING:  # pragma: no cover
    from .server import XThingsServer

# TODO: V0.4.0 add xthings settings

# TODO: V0.6.0 add mDNS support


class XThing:
    # TODO: V0.1.0 add xthing description
    _path: str
    _xthings_blocking_portal: Optional[BlockingPortal] = None
    _observers: dict[str, WeakSet[ObjectSendStream]] = {}
    _ut_probe: Any

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

    def attach_to_app(self, server: XThingsServer, path: str):
        """Add HTTP handlers to the app for this XThing"""
        self._path = path
        self._action_manager = server.action_manager

        for xdescriptor in XThingsDescriptor.get_xdescriptors(self):
            xdescriptor.add_to_app(server.app, self)

        @server.app.get(
            self.path, response_model_exclude_none=True, response_model_by_alias=True
        )
        def thing_description(request: Request):
            return "thing_description"

        @server.app.websocket(self.path + "/ws")
        async def websocket(ws: WebSocket):
            await websocket_endpoint(self, ws)

    def observers(self, attr: str) -> WeakSet[ObjectSendStream[Any]]:
        if attr not in self._observers.keys():
            self._observers[attr] = WeakSet()
        return self._observers[attr]

    def add_observer_by_attr(
        self, attr: str, observer_stream: ObjectSendStream
    ) -> None:
        self.observers(attr).add(observer_stream)

    def remove_observer_by_attr(
        self, attr: str, observer_stream: ObjectSendStream
    ) -> None:
        self.observers(attr).remove(observer_stream)
