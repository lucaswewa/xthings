import asyncio
import socket
import time
from zeroconf import IPVersion, get_all_addresses, Zeroconf, ServiceInfo


def register_mdns(xthing_services, port, properties, server):
    ip_version = IPVersion.V4Only
    mdns_addresses = [
        socket.inet_aton(i)
        for i in get_all_addresses()
        if i not in ("127.0.0.1", "0.0.0.0") and not i.startswith("169.254")
    ]

    infos = []
    for service_type, service_name in xthing_services:
        infos.append(
            ServiceInfo(
                service_type,
                service_name,
                addresses=mdns_addresses,
                port=port,
                properties=properties,
                server=server,
            )
        )

    zeroconf = Zeroconf(ip_version=ip_version)
    for info in infos:
        zeroconf.register_service(info)
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        print("Unregistering...")
        for info in infos:
            zeroconf.unregister_service(info)
        zeroconf.close()


def run_mdns_in_executor(xthing_services, port, properties, server):
    asyncio.get_running_loop().run_in_executor(
        None, register_mdns, xthing_services, port, properties, server
    )
