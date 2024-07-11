from fastapi.testclient import TestClient
import pytest

from xthings.server import XThingsServer
from xthings.xthing import XThing


def test_xthings_server_lifecycle():
    server = XThingsServer()
    with TestClient(server.app):
        assert server._lifecycle_status == "startup..."
        assert server._blocking_portal is not None

    assert server._lifecycle_status == "shutdown..."
    assert server._blocking_portal is None


def test_xthings_server_add_xthing():
    server = XThingsServer()
    xthing = XThing()
    assert xthing.path is None
    server.add_xthing(xthing, "/xthing")
    assert xthing.path == "/xthing"
    assert xthing._xthings_blocking_portal is None

    assert server.xthings["/xthing"] == xthing
    with TestClient(server.app) as client:
        assert xthing._ut_probe == "setup"
        assert xthing._xthings_blocking_portal is not None
        r = client.get("/xthing")
        assert r.status_code == 200
        assert r.json() == "thing_description"
    assert xthing._ut_probe == "shutdown"
    assert xthing._xthings_blocking_portal is None


def test_xthings_server_add_xthing_twice():
    with pytest.raises(KeyError):
        server = XThingsServer()
        xthing = XThing()
        server.add_xthing(xthing, "/xthing")
        server.add_xthing(xthing, "/xthing")
