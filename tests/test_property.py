from fastapi.testclient import TestClient

from xthings.server import XThingsServer
from xthings.xthing import XThing
from xthings.descriptors import PropertyDescriptor
from xthings.decorators import xthings_property
from pydantic import BaseModel


class User(BaseModel):
    id: int
    name: str


user1 = User(id=1, name="John")
user2 = User(id=2, name="Joe")


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
    class MyXThing(XThing):
        p = PropertyDescriptor(User, user1)

    server = XThingsServer()
    xthing = MyXThing()
    server.add_xthing(xthing, "/xthing")

    with TestClient(server.app) as client:
        r = client.get("/xthing/p")
        assert User.model_validate(r.json()) == user1

        client.put("/xthing/p", json=user2.model_dump())
        r = client.get("/xthing/p")
        assert User.model_validate(r.json()) == user2


def test_property_decorator():
    class MyXThing(XThing):
        foo = PropertyDescriptor(User, user1)

        _xyz: User

        def setup(self):
            self._xyz = user1
            return super().setup()

        def teardown(self):
            self._xyz = None
            del self._xyz
            return super().teardown()

        @xthings_property(model=User)
        def xyz(self) -> User:
            return self._xyz

        @xyz.setter
        def xyz(self, v: User):
            self._xyz = v

    server = XThingsServer()

    with MyXThing() as t:
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
