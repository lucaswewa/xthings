from xthings.xthing import XThing
from xthings.descriptors import (
    PropertyDescriptor,
    ActionDescriptor,
    PngImageStreamDescriptor,
)
from xthings.server import XThingsServer
from xthings.decorators import xthings_property, xthings_action
from xthings.action_manager import CancellationToken
from pydantic import BaseModel
from fastapi.responses import HTMLResponse
import numpy as np
import time
import logging
# import threading


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
    png_stream_cv = PngImageStreamDescriptor(ringbuffer_size=100)
    _xyz: User

    def __init__(self, service_type, service_name):
        XThing.__init__(self, service_type, service_name)

    def setup(self):
        super().setup()
        self._streaming = False
        self._delay = 0.1
        self._xyz = user1

        return self

    def teardown(self):
        self._xyz = None
        super().teardown()
        return self

    @xthings_property(model=User)
    def xyz(self):
        return self._xyz

    @xyz.setter  # type: ignore[no-redef]
    def xyz(self, v):
        self._xyz = v

    @xthings_action(input_model=User, output_model=User)
    def func(
        self, s: User, cancellation_token: CancellationToken, logger: logging.Logger
    ):
        t = self.settings["a"]
        logger.info("func start")
        logger.info(f"start to sleep {t} seconds")
        n = 0
        while n < 100:
            time.sleep(t)
            cancellation_token.check(0)
            n += 1
        self.foo = s
        print("end")
        logger.info("func end")
        return s

    @xthings_action(input_model=User, output_model=User)
    def start_png_stream_cv(self, s: User, cancellatioin_token, logger):
        print(self.png_stream_cv, self._streaming, self._delay)
        if not self._streaming:
            self._streaming = True
            while self._streaming:
                frame = np.random.rand(480, 640, 3) * 255
                frame = frame.astype(np.uint8)

                if self.png_stream_cv.add_frame(
                    frame=frame, portal=self._xthings_blocking_portal
                ):
                    self.last_frame_index = self.png_stream_cv.last_frame_i
                    # time.sleep(self._delay)

    @xthings_action(input_model=User, output_model=User)
    def stop_png_stream_cv(self, s: User, cancellation_token, logger):
        print(self.png_stream_cv)
        self._streaming = False


xthings_server = XThingsServer(settings_folder="./settings")
myxthing = MyXThing("_xthings._http._tcp.local.", "myxthing._xthings._http._tcp.local.")
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
