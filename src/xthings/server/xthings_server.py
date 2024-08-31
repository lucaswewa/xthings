"""
A FastAPI server to host the XThings service - XThingsServer
"""

from __future__ import annotations
from anyio.from_thread import BlockingPortal
from contextlib import asynccontextmanager, AsyncExitStack
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, TYPE_CHECKING
from weakref import WeakSet
import os
import yaml

from ..action import ActionManager
from .xthings_zeroconf import run_mdns_in_executor, stop_mdns_thread

if TYPE_CHECKING:  # pragma: no cover
    from ..xthing import XThing

_xthings_servers: WeakSet[XThingsServer] = WeakSet()

port = 8000  # TODO: configurable in settings.yaml


class XThingsServer:
    """An XThingsServer is a FastAPI app, which can hosts one or more XThing(s)"""

    _app: FastAPI
    _lifecycle_status: Optional[str]
    _blocking_portal: Optional[BlockingPortal]
    _xthings: dict[str, XThing]

    def __init__(self, settings_folder: Optional[str] = None):
        self._app = FastAPI(lifespan=self.lifespan)

        self._app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        self._settings_folder = settings_folder or "./settings"
        self._action_manager = ActionManager().attach_to_app(self._app)
        self._blocking_portal: Optional[BlockingPortal] = None
        self._lifecycle_status: str = None
        self._xthings: dict[str, XThing] = {}
        global _xthings_servers
        _xthings_servers.add(self)

    @property
    def app(self):
        return self._app

    @property
    def xthings(self):
        return self._xthings

    @property
    def action_manager(self):
        return self._action_manager

    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        """Manage setup and teardown

        This method performs two important things:
        * It sets up the blocking portal such that background threads can run async code
          in the event loop thread. This is important for events.
        * It runs setup/teardown code for the XThing(s) hosted in this server.
        """
        self._lifecycle_status = "startup..."
        async with BlockingPortal() as portal:
            self._blocking_portal = portal

            # attach the blocking portal to each of the XThing
            for xthing in self._xthings.values():
                xthing._blocking_portal = portal

            async with AsyncExitStack() as stack:
                xthing_services = []
                for xthing in self._xthings.values():
                    await stack.enter_async_context(xthing)
                    xthing_services.append((xthing._service_type, xthing._service_name))
                properties = {"key": "value"}  # TODO: settings.yaml
                server = "myserver.local."  # TODO: settings.yaml
                cancellation_token = run_mdns_in_executor(
                    xthing_services, port, properties, server
                )
                yield
                stop_mdns_thread(cancellation_token)

            # detach the blocking portal from each of the XThing
            for xthing in self._xthings.values():
                xthing._blocking_portal = None

            self._lifecycle_status = "shutdown..."
        self._blocking_portal = None

    def add_xthing(self, xthing: XThing, path: str):
        """Add an XThing to the XThingsServer"""
        if path in self._xthings:
            raise KeyError(f"{path} has already been added to this XThingsServer")
        self._xthings[path] = xthing

        settings_folder = os.path.join(self._settings_folder)
        os.makedirs(settings_folder, exist_ok=True)
        filename = os.path.join(settings_folder, f"{path.strip('/')}.settings.yaml")
        if os.path.exists(filename):
            with open(filename, "r") as f:
                xthing.settings = yaml.safe_load(f)
        else:
            xthing.settings = {}

        xthing.attach_to_app(self, path)
