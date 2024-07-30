from fastapi.testclient import TestClient

from xthings.server import XThingsServer
from xthings.xthing import XThing
from xthings.descriptors import PropertyDescriptor
from xthings import xproperty
from pydantic import BaseModel

service_type = "_http._tcp.local."
service_name = "thing._http._tcp.local."


class User(BaseModel):
    id: int
    name: str


user1 = User(id=1, name="John")
user2 = User(id=2, name="Joe")


class MyXThing(XThing):
    p = PropertyDescriptor(User, user1)
    foo = PropertyDescriptor(User, user1)

    _xyz: User

    def setup(self):
        self._xyz = user1
        return super().setup()

    def teardown(self):
        self._xyz = None
        del self._xyz
        return super().teardown()

    @xproperty(model=User)
    def xyz(self) -> User:
        return self._xyz

    @xyz.setter
    def xyz(self, v: User):
        self._xyz = v


def test_property_initialization():
    p = PropertyDescriptor(User, user1)
    assert isinstance(p, PropertyDescriptor)

    class XT:
        p = PropertyDescriptor(User, user1)

    xt = XT()
    assert xt.p == user1

    xt.p = user2
    assert xt.p == user2


def test_property_add_to_app():
    server = XThingsServer()
    xthing = MyXThing(service_type, service_name)
    server.add_xthing(xthing, "/xthing")

    with TestClient(server.app) as client:
        r = client.get("/xthing/p")
        assert User.model_validate(r.json()) == user1

        client.put("/xthing/p", json=user2.model_dump())
        r = client.get("/xthing/p")
        assert User.model_validate(r.json()) == user2


def test_property_decorator():
    server = XThingsServer()

    with MyXThing(service_type, service_name) as t:
        server.add_xthing(t, "/xthing")
        with TestClient(server.app) as client:
            r = client.get("/xthing/xyz")
            assert User.model_validate(r.json()) == user1

            client.put("/xthing/xyz", json=user2.model_dump())

            r = client.get("/xthing/xyz")
            assert User.model_validate(r.json()) == user2

            r = client.get("/xthing/foo")
            assert User.model_validate(r.json()) == user1

            client.put("/xthing/foo", json=user2.model_dump())
            r = client.get("/xthing/foo")
            assert User.model_validate(r.json()) == user2


def test_property_observer():
    server = XThingsServer()
    xthing = MyXThing(service_type, service_name)
    server.add_xthing(xthing, "/xthing")

    with TestClient(server.app) as client:
        with TestClient(server.app) as client2:
            with client.websocket_connect("/xthing/ws") as ws:
                with client2.websocket_connect("/xthing/ws") as ws2:
                    ws.send_json(
                        {"messageType": "addPropertyObservation", "data": {"xyz": True}}
                    )
                    ws.send_json(
                        {"messageType": "addPropertyObservation", "data": {"foo": True}}
                    )
                    ws2.send_json(
                        {"messageType": "addPropertyObservation", "data": {"xyz": True}}
                    )

                    message = ws.receive_json(mode="text")
                    message = ws.receive_json(mode="text")
                    message = ws2.receive_json(mode="text")

                    client.put("/xthing/xyz", json=user2.model_dump())

                    r = client.get("/xthing/xyz")
                    assert User.model_validate(r.json()) == user2

                    message = ws.receive_json(mode="text")
                    assert message["messageType"] == "propertyStatus"
                    assert User.model_validate(message["data"]["xyz"]) == user2
                    message = ws2.receive_json(mode="text")
                    assert message["messageType"] == "propertyStatus"
                    assert User.model_validate(message["data"]["xyz"]) == user2
