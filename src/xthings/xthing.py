"""
The XThing class
"""

from __future__ import annotations
from anyio.to_thread import run_sync
from anyio.from_thread import BlockingPortal
from fastapi import Request
from typing import Any, TYPE_CHECKING, Optional

from .xthings_server_websocket import websocket_endpoint, WebSocket

if TYPE_CHECKING:  # pragma: no cover
    from .xthings_server import XThingsServer


class XThing:
    _path: Optional[str] = None
    _xthings_blocking_portal: Optional[BlockingPortal] = None

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
        self.shutdown()

    @property
    def path(self):
        return self._path

    def setup(self):
        """Setup the XThing hardware or other initialization operations

        Subclass should override this method.
        """
        self._ut_probe = "setup"

    def shutdown(self):
        """Shutdown the XThing hardware or other deinitialization operations

        Subclass should override this method.
        """
        self._ut_probe = "shutdown"

    def attach_to_app(self, server: XThingsServer, path: str):
        """Add HTTP handlers to the app for this XThing"""
        self._path = path

        @server.app.get(
            self._path, response_model_exclude_none=True, response_model_by_alias=True
        )
        def thing_description(request: Request):
            return "thing_description"

        @server.app.websocket(self.path + "/ws")
        async def websocket(ws: WebSocket):
            await websocket_endpoint(self, ws)
