from __future__ import annotations
from fastapi import FastAPI, Request
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict
from typing import Optional, Any, Sequence, MutableSequence
from typing import TYPE_CHECKING
from typing_extensions import Self
import uuid
from threading import RLock
from pydantic import RootModel
import asyncio
import logging
from pydantic import model_validator
from collections import deque

if TYPE_CHECKING:  # pragma: no cover
    from .descriptors import ActionDescriptor
    from .xthing import XThing


class InvocationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ERROR = "error"


class LogRecord(BaseModel):
    """A model to serialise logging.LogRecord objects"""

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    message: str
    levelname: str
    levelno: int
    lineno: int
    filename: str
    created: datetime

    @model_validator(mode="before")
    @classmethod
    def generate_message(cls, data: Any):
        if not hasattr(data, "message"):
            if isinstance(data, logging.LogRecord):
                try:
                    data.message = data.getMessage()
                except (ValueError, TypeError) as e:
                    # too many args causes an error - but errors
                    # in validation can be a problem for us:
                    # it will cause 500 errors when retrieving
                    # the invocation.
                    # This way, you can find and fix the source.
                    data.message = (
                        f"Error constructing message ({e}) " f"from {data!r}."
                    )
        return data


class InvocationModel(BaseModel):
    status: InvocationStatus
    id: uuid.UUID
    action: str
    href: str
    timeStarted: Optional[datetime]
    timeRequested: Optional[datetime]
    timeCompleted: Optional[datetime]
    input: Optional[Any]
    output: Optional[Any]
    log: Sequence[LogRecord]


class EmptyObject(BaseModel):
    model_config = ConfigDict(extra="allow")


class EmptyInput(RootModel):
    root: Optional[EmptyObject] = None


def invocation_logger(id) -> logging.Logger:
    logger = logging.getLogger(f"xthings.action.{id}")
    logger.setLevel(logging.INFO)
    return logger


class DequeLogHandler(logging.Handler):
    def __init__(self, dest: MutableSequence, level=logging.INFO):
        logging.Handler.__init__(self)
        self.setLevel(level)
        self.dest = dest

    def emit(self, record):
        self.dest.append(record)


class Invocation:
    """The Invocation of an action function runs in a thread executor"""

    # TODO: V0.6.0 add Cancellation
    def __init__(
        self,
        action: ActionDescriptor,
        xthing: XThing,
        input: Optional[BaseModel] = None,
        id: Optional[uuid.UUID] = None,
    ):
        self._action = action
        self._xthing = xthing
        self._input = input if input is not None else EmptyInput()
        self._id = id

        self._status_lock = RLock()
        self._status = InvocationStatus.PENDING
        self._request_time: datetime = datetime.now()
        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None
        self._exception: Optional[Exception] = None
        self._return_value: Optional[Any] = None

        self._log: deque = deque(maxlen=1000)

    @property
    def id(self):
        return self._id

    @property
    def input(self) -> Any:
        return self._input

    @property
    def output(self) -> Any:
        return self._return_value

    def response(self, request: Optional[Request] = None):
        return self._action._invocation_model(
            status=self._status,
            id=self.id,
            action=self._xthing.path + self._action.name,
            href=f"/actions/{self.id}",
            timeStarted=self._start_time,
            timeCompleted=self._end_time,
            timeRequested=self._request_time,
            input=self.input,
            output=self.output,
            log=self._log,
        )

    def run(self) -> None:
        handler = DequeLogHandler(dest=self._log)
        logger = invocation_logger(self.id)
        logger.addHandler(handler)

        with self._status_lock:
            self._status = InvocationStatus.RUNNING
            self._start_time = datetime.now()
            self._action.emit_changed_event(self._xthing, self._status)

        try:
            kwargs = self._input
            result = self._action.__get__(xthing_obj=self._xthing)(kwargs, logger)

            with self._status_lock:
                self._status = InvocationStatus.COMPLETED
                self._return_value = result
            self._action.emit_changed_event(self._xthing, self._status)
        except Exception as e:
            logger.error("invocation error")
            with self._status_lock:
                self._status = InvocationStatus.ERROR
                self._exception = e
            self._action.emit_changed_event(self._xthing, self._status)
        finally:
            with self._status_lock:
                self._end_time = datetime.now()


class ActionManager:
    # TODO: V0.5.0 endpoint for invocation filteration by action, expire invocation, delete expired invocation
    def __init__(self):
        self._invocations = {}
        self._invocations_lock = asyncio.Lock()

    async def invoke_action(
        self,
        action: ActionDescriptor,
        xthing: XThing,
        input: Optional[BaseModel],
        id: uuid.UUID,
    ):
        thread = Invocation(action, xthing, input, id)
        asyncio.get_running_loop().run_in_executor(
            None, action.emit_changed_event, xthing, InvocationStatus.PENDING
        )

        asyncio.get_running_loop().run_in_executor(None, thread.run)
        async with self._invocations_lock:
            self._invocations[str(thread.id)] = thread
        return thread

    async def list_invocation(self):
        async with self._invocations_lock:
            return [i.response() for i in self._invocations.values()]

    def attach_to_app(self, app: FastAPI) -> Self:
        @app.get("/invocations", response_model=list[InvocationModel])
        async def list_all_invocations(request: Request):
            return await self.list_invocation()

        return self
