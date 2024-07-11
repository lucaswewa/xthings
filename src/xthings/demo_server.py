from xthings.xthing import XThing
from xthings.property import PropertyDescriptor
from xthings.server import XThingsServer


class MyXThing(XThing):
    foo = PropertyDescriptor(1)


xthings_server = XThingsServer()
myxthing = MyXThing()
xthings_server.add_xthing(myxthing, "/xthing")
print(myxthing.foo)
myxthing.foo = 2

app = xthings_server.app
