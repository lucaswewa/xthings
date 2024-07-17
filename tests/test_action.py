from fastapi.testclient import TestClient

from xthings.server import XThingsServer
from xthings.xthing import XThing
from xthings.descriptors import ActionDescriptor
from pydantic import StrictInt
from xthings.decorators import xthings_action


def test_action_initialization():
    ad = ActionDescriptor(
        lambda x: x + 1, input_model=StrictInt, output_model=StrictInt
    )
    assert isinstance(ad, ActionDescriptor)

    class XT:
        ad = ActionDescriptor(
            lambda xthing, x, logger: x + 1,
            input_model=StrictInt,
            output_model=StrictInt,
        )

    xt = XT()
    assert xt.ad(1, None) == 2


def test_action_add_to_app():
    class MyXThing(XThing):
        ad = ActionDescriptor(
            lambda xthing, x, logger: x + 1,
            input_model=StrictInt,
            output_model=StrictInt,
        )

        @xthings_action(input_model=StrictInt, output_model=StrictInt)
        def func(self, i: StrictInt, logger) -> StrictInt:
            return i + 1

        @xthings_action(input_model=StrictInt, output_model=StrictInt)
        def func_error(self, i: StrictInt, logger) -> StrictInt:
            raise Exception("error")
            return i + 1

    server = XThingsServer()
    xthing = MyXThing()
    server.add_xthing(xthing, "/xthing")

    with TestClient(server.app) as client:
        r = client.post("/xthing/ad", json=1)
        print(1)
        assert r.status_code == 201

        r = client.get("/xthing/ad")
        print(1)
        assert r.json() == []

        r = client.get("/invocations")
        print(1)
        assert r.json()[0]["status"] == "completed"

        r = client.post("/xthing/func", json=1)
        print(1)
        assert r.status_code == 201

        r = client.get("/xthing/func")
        print(1)
        assert r.json() == []

        r = client.get("/invocations")
        print(1)
        assert r.json()[1]["status"] == "completed"

        r = client.post("/xthing/func_error", json=1)
        print(1)
        assert r.status_code == 201

        r = client.get("/xthing/func_error")
        print(1)
        assert r.json() == []

        r = client.get("/invocations")
        print(1)
        assert r.json()[2]["status"] == "error"
