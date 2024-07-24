from zeroconf import ServiceBrowser, Zeroconf, IPVersion
from time import sleep


def on_service_state_change(zeroconf, service_type, name, state_change):
    print(service_type, name, state_change)
    serviceinfo = zeroconf.get_service_info(
        service_type,
        name,
    )
    print(serviceinfo)
    print(serviceinfo.parsed_addresses())


zeroconf = Zeroconf(ip_version=IPVersion.V4Only)

# Service broswer
services = ["_xthings._tcp.local."]
broswer = ServiceBrowser(zeroconf, services, handlers=[on_service_state_change])

try:
    while True:
        sleep(0.1)
except KeyboardInterrupt:
    pass
finally:
    zeroconf.close()
