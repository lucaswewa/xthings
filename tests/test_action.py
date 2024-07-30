from fastapi.testclient import TestClient

from xthings.server import XThingsServer
from xthings.xthing import XThing
from xthings.descriptors import ActionDescriptor
from pydantic import StrictInt
from xthings import xaction
import pytest
import uuid
import time

service_type = "_http._tcp.local."
service_name = "thing._http._tcp.local."


class MyXThing(XThing):
    ad = ActionDescriptor(
        lambda xthing, x, cancellation_token, logger: x + 1,
        input_model=StrictInt,
        output_model=StrictInt,
    )

    @xaction(input_model=StrictInt, output_model=StrictInt)
    def func(self, i: StrictInt, cancellation_token, logger) -> StrictInt:
        return i + 1

    @xaction(input_model=StrictInt, output_model=StrictInt)
    def func_error(self, i: StrictInt, cancellation_token, logger) -> StrictInt:
        raise Exception("error")
        return i + 1

    @xaction(input_model=StrictInt, output_model=StrictInt)
    def func_slow(self, i: StrictInt, cancellation_token, logger) -> StrictInt:
        for i in range(10):
            time.sleep(0)
            cancellation_token.check(0)

        return i + 1


server: XThingsServer
xthing: MyXThing


@pytest.fixture(autouse=True)
def setup():
    global server, xthing
    server = XThingsServer()
    xthing = MyXThing(service_type, service_name)
    server.add_xthing(xthing, "/xthing")


def test_action_initialization():
    ad = ActionDescriptor(
        lambda xthing, x, ct, logger: x + 1,
        input_model=StrictInt,
        output_model=StrictInt,
    )
    assert isinstance(ad, ActionDescriptor)

    class XT:
        ad = ActionDescriptor(
            lambda xthing, x, cancellation_token, logger: x + 1,
            input_model=StrictInt,
            output_model=StrictInt,
        )

    xt = XT()
    assert xt.ad(1, None, None) == 2


def test_action_add_to_app():
    with TestClient(server.app) as client:
        r = client.post("/xthing/ad", json=1)
        assert r.status_code == 201

        r = client.get("/xthing/ad")
        assert len(r.json()) == 1

        r = client.get("/invocations")
        assert r.json()[0]["status"] == "completed"

        invocation_id = r.json()[0]["id"]
        r = client.get(f"/invocations/{invocation_id}")
        assert r.json()["status"] == "completed"

        r = client.delete(f"/invocations/{invocation_id}")
        assert r.status_code == 200

        invocation_id = str(uuid.uuid4())
        r = client.get(f"/invocations/{invocation_id}")
        assert r.status_code == 404

        r = client.post("/xthing/func_slow", json=1)
        assert r.status_code == 201
        r = client.get("/xthing/func_slow")
        assert len(r.json()) == 1
        invocation_id = r.json()[0]["id"]
        r = client.delete(f"/invocations/{invocation_id}")
        assert r.status_code == 200
        # r = client.get(f"/invocations/{invocation_id}")
        # assert r.json()["status"] == "completed"

        r = client.post("/xthing/func", json=1)
        assert r.status_code == 201

        r = client.get("/xthing/func")
        assert len(r.json()) == 1

        r = client.get("/invocations")
        assert r.json()[1]["status"] == "completed"

        r = client.post("/xthing/func_error", json=1)
        assert r.status_code == 201

        r = client.get("/xthing/func_error")
        assert len(r.json()) == 1

        r = client.get("/invocations")
        r = client.get(
            "/invocations"
        )  # Fixme: get twice to wait for next task in the event loop
        assert r.json()[3]["status"] == "error"
