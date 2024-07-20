#!/usr/bin/env python3
"""Example of announcing 250 services (in this case, a fake HTTP server)."""

import argparse
import asyncio
import logging
import socket
from typing import List, Optional

from zeroconf import IPVersion
from zeroconf.asyncio import AsyncServiceInfo, AsyncZeroconf


class AsyncRunner:
    def __init__(self, ip_version: IPVersion) -> None:
        self.ip_version = ip_version
        self.aiozc: Optional[AsyncZeroconf] = None

    async def register_services(self, infos: List[AsyncServiceInfo]) -> None:
        self.aiozc = AsyncZeroconf(ip_version=self.ip_version)
        tasks = [self.aiozc.async_register_service(info) for info in infos]
        background_tasks = await asyncio.gather(*tasks)
        await asyncio.gather(*background_tasks)
        while True:
            await asyncio.sleep(1)

    async def unregister_services(self, infos: List[AsyncServiceInfo]) -> None:
        assert self.aiozc is not None
        tasks = [self.aiozc.async_unregister_service(info) for info in infos]
        background_tasks = await asyncio.gather(*tasks)
        await asyncio.gather(*background_tasks)
        await self.aiozc.async_close()


def run_mdns_task(xthing_services):  # service_type, service_name):
    ip_version = IPVersion.V4Only

    infos = []
    for service_type, service_name in xthing_services:
        infos.append(
            AsyncServiceInfo(
                service_type,
                service_name,
                addresses=[socket.inet_aton("127.0.0.1")],
                port=80,
                properties={"path": "/myxthing/"},
                server="zcdemohost.local.",
            )
        )
    loop = asyncio.get_event_loop()
    runner = AsyncRunner(ip_version)

    loop.create_task(runner.register_services(infos))
