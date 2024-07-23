import asyncio
import socket
from typing import List, Optional

from zeroconf import IPVersion, get_all_addresses
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


def run_mdns_task(xthing_services: list[tuple[str, str]], port):
    ip_version = IPVersion.V4Only

    mdns_addresses = [
        socket.inet_aton(i)
        for i in get_all_addresses()
        if i not in ("127.0.0.1", "0.0.0.0") and not i.startswith("169.254")
    ]

    infos = []
    for service_type, service_name in xthing_services:
        infos.append(
            AsyncServiceInfo(
                service_type,
                service_name,
                addresses=mdns_addresses,
                port=port,
            )
        )

    runner = AsyncRunner(ip_version)

    asyncio.get_running_loop().create_task(runner.register_services(infos))
