from fastapi.testclient import TestClient

from xthings.server import XThingsServer
from xthings.xthing import XThing
from xthings.descriptors import ActionDescriptor


def test_action_initialization():
    ad = ActionDescriptor(lambda x: x + 1)
    assert isinstance(ad, ActionDescriptor)

    class XT:
        ad = ActionDescriptor(lambda xthing, x: x + 1)

    xt = XT()
    assert xt.ad(1) == 2


def test_action_add_to_app():
    class MyXThing(XThing):
        ad = ActionDescriptor(lambda xthing, x: x + 1)

    server = XThingsServer()
    xthing = MyXThing()
    server.add_xthing(xthing, "/xthing")

    with TestClient(server.app) as client:
        r = client.post("/xthing/ad", json=1)
        assert r.status_code == 201

        r = client.get("/xthing/ad")
        assert r.json() == []
