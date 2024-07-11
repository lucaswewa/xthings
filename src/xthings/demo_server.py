from xthings.xthing import XThing
from xthings.descriptors import PropertyDescriptor, ActionDescriptor
from xthings.server import XThingsServer
from xthings.decorators import xthings_property


def func(xthing, s):
    import time

    print(f"start to sleep {s} seconds")
    time.sleep(s)
    xthing.foo = s
    print("end")


class MyXThing(XThing):
    foo = PropertyDescriptor(1)
    bar = ActionDescriptor(func)

    def __init__(self) -> None:
        self._xyz = 123

    @xthings_property
    def xyz(self):
        return self._xyz

    @xyz.setter  # type: ignore[no-redef]
    def xyz(self, v):
        self._xyz = v


xthings_server = XThingsServer()
with MyXThing() as myxthing:
    xthings_server.add_xthing(myxthing, "/xthing")
    print(myxthing.foo)
    myxthing.foo = 2

    app = xthings_server.app
