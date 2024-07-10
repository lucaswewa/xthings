from fastapi.testclient import TestClient
from xthings.xthings_server import XThingsServer
from xthings.xthing import XThing
import pytest
from typing import Optional

xthing: Optional[XThing]
server: Optional[XThingsServer]


@pytest.fixture(autouse=True)
def setup_teardown():
    global xthing, server
    xthing = XThing()
    server = XThingsServer()
    server.add_xthing(xthing, "/xthing")
    yield
    xthing = None
    server = None


def test_websocket_observerproperty():
    with TestClient(server.app) as client:
        with client.websocket_connect("/xthing/ws") as ws:
            ws.send_json(
                {"messageType": "addPropertyObservation", "data": {"foo": True}}
            )

            message = ws.receive_json(mode="text")
            assert message["status"] == "success"


def test_websocket_observeraction():
    with TestClient(server.app) as client:
        with client.websocket_connect("/xthing/ws") as ws:
            ws.send_json({"messageType": "addActionObservation", "data": {"bar": True}})

            message = ws.receive_json(mode="text")
            assert message["status"] == "success"


def test_websocket_observe_errors():
    with TestClient(server.app) as client:
        with client.websocket_connect("/xthing/ws") as ws:
            ws.send_json({"missingMessageTypeKey": "foobar"})
            message = ws.receive_json(mode="text")
            assert message["status"] == "error"
            assert message["errorMessage"] == "BadKey"

            ws.send_json({"messageType": "foobar"})
            message = ws.receive_json(mode="text")
            assert message["status"] == "error"
            assert message["errorMessage"] == "Bad messateType value"

            ws.send_json(
                {"messageType": "addActionObservation", "need_data_field": "something"}
            )
            message = ws.receive_json(mode="text")
            assert message["status"] == "error"
            assert message["errorMessage"] == "BadKey"

            ws.send_text("jsonencoder error")
            message = ws.receive_json(mode="text")
            assert message["status"] == "error"
            assert message["errorMessage"] == "JSONDecoderError"


def test_websocket_observe_KeyError():
    with TestClient(server.app) as client:
        with client.websocket_connect("/xthing/ws") as ws:
            ws.send_json({"missingMessageTypeKey": "foobar"})
            message = ws.receive_json(mode="text")
            assert message["status"] == "error"
            assert message["errorMessage"] == "BadKey"

            ws.send_json({"messageType": "foobar"})
            message = ws.receive_json(mode="text")
            assert message["status"] == "error"
            assert message["errorMessage"] == "Bad messateType value"

            ws.send_json(
                {"messageType": "addActionObservation", "need_data_field": "something"}
            )
            message = ws.receive_json(mode="text")
            assert message["status"] == "error"
            assert message["errorMessage"] == "BadKey"
