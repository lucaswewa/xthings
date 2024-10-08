from fastapi.testclient import TestClient
import pytest

from xthings.server import XThingsServer
from xthings.xthing import XThing

service_type = "_http._tcp.local."
service_name = "thing._http._tcp.local."


server: XThingsServer
xthing: XThing


@pytest.fixture(autouse=True)
def setup():
    global server, xthing
    server = XThingsServer()
    xthing = XThing(service_type, service_name)
    server.add_xthing(xthing, "/xthing")


def test_xthings_server_add_xthing():
    assert xthing.path == "/xthing"
    assert xthing._blocking_portal is None

    assert server.xthings["/xthing"] == xthing
    with TestClient(server.app) as client:
        assert xthing._ut_probe == "setup"
        assert xthing._blocking_portal is not None
        r = client.get("/xthing")
        assert r.status_code == 200
        # assert r.json() == {"properties": {}, "actions": {}, "streams": {}}
    assert xthing._ut_probe == "shutdown"
    assert xthing._blocking_portal is None


def test_xthings_server_lifecycle():
    with TestClient(server.app):
        assert server._lifecycle_status == "startup..."
        assert server._blocking_portal is not None

    assert server._lifecycle_status == "shutdown..."
    assert server._blocking_portal is None


def test_xthings_server_add_xthing_twice():
    with pytest.raises(KeyError):
        server = XThingsServer()
        xthing = XThing(service_type, service_name)
        server.add_xthing(xthing, "/xthing")
        server.add_xthing(xthing, "/xthing")
