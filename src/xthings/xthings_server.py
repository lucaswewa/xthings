"""
A FastAPI server to host the XThings service - XThingsServer
"""

from __future__ import annotations
from anyio.from_thread import BlockingPortal
from contextlib import asynccontextmanager, AsyncExitStack
from fastapi import FastAPI
from weakref import WeakSet

_xthings_servers: WeakSet[XThingsServer] = WeakSet()

class XThingsServer:
    """An XThingsServer is a FastAPI app, which can hosts one or more XThing(s)
    """
    _app: FastAPI
    _lifecycle_status: str

    def __init__(self):
        self._app = FastAPI(lifespan=self.lifespan)

        self._blocking_portal: BlockingPortal = None
        self._lifecycle_status: str = None
        global _xthings_servers
        _xthings_servers.add(self)

    @property
    def app(self):
        return self._app
    
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

            # TODO: attach the blocking portal to each of the XThing

            async with AsyncExitStack() as stack:
                yield

            # TODO: __aenter__ and __aexit__ each of the XThing: await stack.enter_async_context(thing)
            # TODO: detach the blocking portal from each of the XThing

            self._lifecycle_status = "shutdown..."
        self._blocking_portal = None
