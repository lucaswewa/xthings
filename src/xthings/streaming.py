from dataclasses import dataclass
from datetime import datetime
from typing import (
    AsyncIterator,
    Optional,
)
from fastapi.responses import StreamingResponse
import threading

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from anyio.from_thread import BlockingPortal
import anyio

import numpy as np


@dataclass
class RingBuffEntry:
    frame: bytes
    timestamp: datetime
    index: int
    readers_refcount: int = 0


class ImageStreamResponse(StreamingResponse):
    media_type = "multipart/x-mixed-replace; boundary=frame"

    def __init__(
        self, gen: AsyncGenerator[bytes, None], get_content_type, status_code: int = 200
    ):
        self.frame_async_generator = gen
        self.get_content_type = get_content_type
        StreamingResponse.__init__(
            self,
            self.image_generator(),
            media_type=self.media_type,
            status_code=status_code,
        )

    async def image_generator(self) -> AsyncGenerator[bytes, None]:
        async for frame in self.frame_async_generator:
            yield b"--frame\r\nContent-Type: " + self.get_content_type() + b"\r\n\r\n"
            yield frame
            yield b"\r\n"


class ImageStream:
    def __init__(
        self,
        imencode_func,
        stream_response_type_func,
        get_content_type_func,
        ringbuffer_size: int = 10,
    ):
        self._lock = threading.Lock()
        self.condition = anyio.Condition()
        self._ringbuffer: list[RingBuffEntry] = []
        self._streaming = False
        self.imencode = imencode_func
        self.stream_response_type = stream_response_type_func
        self.get_content_type = get_content_type_func

        self.reset(ringbuffer_size=ringbuffer_size)

    def reset(self, ringbuffer_size: Optional[int] = None):
        with self._lock:
            self._streaming = True
            n = ringbuffer_size or len(self._ringbuffer)
            self.last_frame_i = -1
            self._ringbuffer = [
                RingBuffEntry(
                    frame=b"",
                    index=self.last_frame_i,
                    timestamp=datetime.min,
                )
                for i in range(n)
            ]

    def stop(self):
        with self._lock:
            self._streaming = False

    async def ringbuffer_entry(self, i: int) -> RingBuffEntry:
        """Return the `i`th frame acquired by the camera"""
        if i < 0:
            raise ValueError("i must be >= 0")
        if i < self.last_frame_i - len(self._ringbuffer) + 2:
            raise ValueError("the ith frame has been overwritten")
        if i > self.last_frame_i:
            # TODO: await the ith frame
            raise ValueError("the ith frame has not yet been acquired")
        entry = self._ringbuffer[i % len(self._ringbuffer)]
        if entry.index != i:
            raise ValueError("the ith frame has been overwritten")
        return entry

    @asynccontextmanager
    async def buffer_for_reading(self, i: int) -> AsyncIterator[bytes]:
        """Yields the ith frame as a bytes object"""
        entry = await self.ringbuffer_entry(i)
        try:
            entry.readers_refcount += 1
            yield entry.frame
        finally:
            entry.readers_refcount -= 1

    async def next_frame(self) -> int:
        async with self.condition:
            await self.condition.wait()
            return self.last_frame_i

    async def frame_async_generator(self) -> AsyncGenerator[bytes, None]:
        while self._streaming:
            try:
                i = await self.next_frame()
                async with self.buffer_for_reading(i) as frame:
                    yield frame
            except Exception:
                return

    async def image_stream_response(self) -> ImageStreamResponse:
        return ImageStreamResponse(self.frame_async_generator(), self.get_content_type)

    def add_frame(self, frame: np.ndarray, portal: BlockingPortal) -> bool:
        """Add a frame to the ring buffer"""
        with self._lock:
            # Return the next buffer in the ringbuffer to write to
            entry = self._ringbuffer[(self.last_frame_i + 1) % len(self._ringbuffer)]
            if entry.readers_refcount > 0:
                raise RuntimeError("Cannot write to ringbuffer while it is being read")
            entry.timestamp = datetime.now()
            success, array = self.imencode(frame)
            if success:
                entry.frame = array.tobytes()
                entry.index = self.last_frame_i + 1
                portal.start_task_soon(self.notify_new_frame, entry.index)

            return success

    async def notify_new_frame(self, i):
        """Notify any waiting tasks that a new frame is available

        This method runs in the event loop thread."""
        async with self.condition:
            self.last_frame_i = i
            self.condition.notify_all()
