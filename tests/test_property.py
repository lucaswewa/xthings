from fastapi.testclient import TestClient

from xthings.server import XThingsServer
from xthings.xthing import XThing
from xthings.descriptors import PropertyDescriptor
from xthings.decorators import xthings_property


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


def test_property_decorator():
    class MyXThing(XThing):
        foo = PropertyDescriptor(1)

        def __init__(self) -> None:
            self._xyz = 123

        @xthings_property
        def xyz(self):
            return self._xyz

        @xyz.setter
        def xyz(self, v):
            self._xyz = v

    server = XThingsServer()

    with MyXThing() as t:
        server.add_xthing(t, "/xthing")
        with TestClient(server.app) as client:
            r = client.get("/xthing/xyz")
            assert r.json() == 123

            client.put("/xthing/xyz", json=321)

            r = client.get("/xthing/xyz")
            assert r.json() == 321
