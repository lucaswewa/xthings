from fastapi.testclient import TestClient

from xthings.server import XThingsServer
from xthings.xthing import XThing
from xthings.descriptors import ActionDescriptor, PngImageStreamDescriptor
from pydantic import StrictInt
from xthings import xaction
import pytest
import time
import numpy as np


service_type = "_http._tcp.local."
service_name = "thing._http._tcp.local."


class MyXThing(XThing):
    ad = ActionDescriptor(
        lambda xthing, x, cancellation_token, logger: x + 1,
        input_model=StrictInt,
        output_model=StrictInt,
    )
    png_stream_cv = PngImageStreamDescriptor(ringbuffer_size=100)

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

    @xaction(input_model=StrictInt, output_model=StrictInt)
    def start_png_stream_cv(self, s: StrictInt, cancellatioin_token, logger):
        if not self._streaming:
            self._streaming = True
            while self._streaming:
                frame = np.random.rand(480, 640, 3) * 255
                frame = frame.astype(np.uint8)

                if self.png_stream_cv.add_frame(frame=frame):
                    self.last_frame_index = self.png_stream_cv.last_frame_i

    @xaction(input_model=StrictInt, output_model=StrictInt)
    def stop_png_stream_cv(self, s: StrictInt, cancellation_token, logger):
        print(self.png_stream_cv)
        self._streaming = False


server: XThingsServer
xthing: MyXThing


@pytest.fixture(autouse=True)
def setup():
    global server, xthing
    server = XThingsServer()
    xthing = MyXThing(service_type, service_name)
    server.add_xthing(xthing, "/xthing")


def test_action_add_to_app():
    with TestClient(server.app) as client:
        r = client.post("/xthing/start_png_stream_cv", json=1)
        assert r.status_code == 201
        frame = np.random.rand(480, 640, 3) * 255
        frame = frame.astype(np.uint8)
        xthing.png_stream_cv.add_frame(frame=frame)

        xthing.png_stream_cv.stop()
