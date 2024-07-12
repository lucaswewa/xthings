from xthings.xthing import XThing
from xthings.descriptors import PropertyDescriptor, ActionDescriptor
from xthings.server import XThingsServer
from xthings.decorators import xthings_property
from pydantic import BaseModel


class User(BaseModel):
    id: int
    name: str


def func(xthing, s):
    import time

    print(f"start to sleep {s} seconds")
    time.sleep(s)
    xthing.foo = s
    print("end")


user1 = User(id=1, name="Jane")
user2 = User(id=2, name="John")


class MyXThing(XThing):
    foo = PropertyDescriptor(User, User(id=1, name="John"))
    bar = ActionDescriptor(func)
    _xyz: User

    def setup(self):
        self._xyz = user1
        return super().setup()

    @xthings_property(model=User)
    def xyz(self):
        return self._xyz

    @xyz.setter  # type: ignore[no-redef]
    def xyz(self, v):
        self._xyz = v


xthings_server = XThingsServer()
with MyXThing() as myxthing:
    xthings_server.add_xthing(myxthing, "/xthing")
    print(myxthing.foo)
    myxthing.foo = User(id=2, name="Smith")

    app = xthings_server.app
