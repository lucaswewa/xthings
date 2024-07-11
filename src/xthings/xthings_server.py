"""
A FastAPI server to host the XThings service - XThingsServer
"""

from __future__ import annotations
from anyio.from_thread import BlockingPortal
from contextlib import asynccontextmanager, AsyncExitStack
from fastapi import FastAPI
from typing import Optional
from weakref import WeakSet

from .xthing import XThing

_xthings_servers: WeakSet[XThingsServer] = WeakSet()


class XThingsServer:
    """An XThingsServer is a FastAPI app, which can hosts one or more XThing(s)"""

    _app: FastAPI
    _lifecycle_status: Optional[str]
    _blocking_portal: Optional[BlockingPortal]
    _xthings: dict[str, XThing]

    def __init__(self, settings: Optional[str] = ""):
        self._app = FastAPI(lifespan=self.lifespan)

        self._blocking_portal: Optional[BlockingPortal] = None
        self._lifecycle_status: str = None
        self._xthings: dict[str, XThing] = {}
        global _xthings_servers
        _xthings_servers.add(self)
        print(settings)

    @property
    def app(self):
        return self._app

    @property
    def xthings(self):
        return self._xthings

    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        """Manage setup and teardown

        This does two important things:
        * It sets up the blocking portal so background threads can run async code.
          This is important for events.
        * It runs setup/teardown code for the XThing(s) hosted in this server.
        """
        self._lifecycle_status = "startup..."
        async with BlockingPortal() as portal:
            self._blocking_portal = portal

            # attach the blocking portal to each of the XThing
            for xthing in self._xthings.values():
                xthing._xthings_blocking_portal = portal

            async with AsyncExitStack() as stack:
                for xthing in self._xthings.values():
                    await stack.enter_async_context(xthing)

                yield

            # detach the blocking portal from each of the XThing
            for xthing in self._xthings.values():
                xthing._xthings_blocking_portal = None

            self._lifecycle_status = "shutdown..."
        self._blocking_portal = None

    def add_xthing(self, xthing: XThing, path: str):
        """Add an XThing to the XThingsServer"""
        if path in self._xthings:
            raise KeyError(f"{path} has already been added to this XThingsServer")
        self._xthings[path] = xthing

        xthing.attach_to_app(self, path)
