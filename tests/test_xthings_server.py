from fastapi.testclient import TestClient

from xthings.xthings_server import XThingsServer

def test_xthings_server_lifecycle():
    server = XThingsServer()
    with TestClient(server.app):
        assert server._lifecycle_status == "startup..."
        assert server._blocking_portal is not None
        
    assert server._lifecycle_status == "shutdown..."
    assert server._blocking_portal is None
