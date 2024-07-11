from fastapi.testclient import TestClient

from xthings.server import XThingsServer
from xthings.xthing import XThing
from xthings.property import PropertyDescriptor


def test_property_initialization():
    p = PropertyDescriptor(1)
    assert isinstance(p, PropertyDescriptor)

    class XT:
        p = PropertyDescriptor(1)

    xt = XT()
    assert xt.p == 1

    xt.p = 2
    assert xt.p == 2


def test_property_add_to_app():
    class MyXThing(XThing):
        p = PropertyDescriptor(1)

    server = XThingsServer()
    xthing = MyXThing()
    server.add_xthing(xthing, "/xthing")

    with TestClient(server.app) as client:
        r = client.get("/xthing/p")
        assert r.json() == 1

        client.put("/xthing/p", json=2)
        r = client.get("/xthing/p")
        assert r.json() == 2
