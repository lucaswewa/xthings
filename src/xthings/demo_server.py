from xthings.xthing import XThing
from xthings.property import PropertyDescriptor
from xthings.action import ActionDescriptor
from xthings.server import XThingsServer


def func(xthing, s):
    import time

    print(f"start to sleep {s} seconds")
    time.sleep(s)
    xthing.foo = s
    print("end")


class MyXThing(XThing):
    foo = PropertyDescriptor(1)
    bar = ActionDescriptor(func)


xthings_server = XThingsServer()
myxthing = MyXThing()
xthings_server.add_xthing(myxthing, "/xthing")
print(myxthing.foo)
myxthing.foo = 2

app = xthings_server.app
