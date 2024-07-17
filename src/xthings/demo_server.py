from xthings.xthing import XThing
from xthings.descriptors import PropertyDescriptor, ActionDescriptor
from xthings.server import XThingsServer
from xthings.decorators import xthings_property, xthings_action
from pydantic import BaseModel
from fastapi.responses import HTMLResponse


class User(BaseModel):
    id: int
    name: str


def func(xthing, s: User):
    import time

    print(f"start to sleep {s} seconds")
    time.sleep(s.id)
    xthing.foo = s
    print("end")


user1 = User(id=1, name="Jane")
user2 = User(id=2, name="John")


class MyXThing(XThing):
    foo = PropertyDescriptor(User, User(id=1, name="John"))
    bar = ActionDescriptor(func, input_model=User, output_model=User)
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

    @xthings_action(input_model=User, output_model=User)
    def func(self, s: User, logger):
        import time

        logger.info("func start")
        print(f"start to sleep {s} seconds")
        time.sleep(s.id)
        self.foo = s
        print("end")
        logger.info("func end")
        return s


xthings_server = XThingsServer()
with MyXThing() as myxthing:
    xthings_server.add_xthing(myxthing, "/xthing")
    myxthing.foo = User(id=2, name="Smith")

    app = xthings_server.app

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var ws = new WebSocket("ws://localhost:8000/xthing/ws");
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""

"""
{"messageType": "addPropertyObservation", "data": {"xyz": true}}
{"messageType": "addActionObservation", "data": {"func": true}}
"""


@app.get("/wsclient", tags=["websockets"])
async def get():
    return HTMLResponse(html)
