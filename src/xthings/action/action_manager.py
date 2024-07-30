from __future__ import annotations
from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict
from typing import Optional, Any, Sequence, MutableSequence
from typing import TYPE_CHECKING, Callable
from typing_extensions import Self
import uuid
from threading import RLock
from pydantic import RootModel
import asyncio
import logging
from pydantic import model_validator
from collections import deque
import threading
from functools import partial

from ..utils import pathjoin
from ..errors import InvocationCancelledError

if TYPE_CHECKING:  # pragma: no cover
    from ..descriptors import ActionDescriptor
    from ..xthing import XThing


EventHandle = Callable[[str], None]


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


class CancellationToken:
    def __init__(self, id: uuid.UUID):
        self._event: threading.Event = threading.Event()
        self._invocation_id = id

    def check(self, timeout: float):
        if self._event.wait(timeout):
            raise InvocationCancelledError("The actioin was cancelled.")


class Invocation:
    """The Invocation of an action function runs in a thread executor"""

    def __init__(
        self,
        action: ActionDescriptor,
        xthing: XThing,
        input: Optional[BaseModel] = None,
        id: Optional[uuid.UUID] = None,
        cancellation_token: Optional[CancellationToken] = None,
    ):
        self._action = action
        self._xthing = xthing
        self._input = input if input is not None else EmptyInput()
        self._id = id
        self._cancellation_token = cancellation_token

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
    def action(self):
        return self._action

    @property
    def xthing(self):
        return self._xthing

    @property
    def input(self) -> Any:
        return self._input

    @property
    def output(self) -> Any:
        return self._return_value

    def cancel(self):
        if self._cancellation_token is not None:
            self._cancellation_token._event.set()

    def response(self, request: Optional[Request] = None):
        return self._action._invocation_model(
            status=self._status,
            id=self.id,
            action=pathjoin(self._xthing.path, self._action.name),
            href=f"/invocations/{self.id}",
            timeStarted=self._start_time,
            timeCompleted=self._end_time,
            timeRequested=self._request_time,
            input=self.input if not isinstance(self.input, EmptyInput) else None,
            output=self.output,
            log=self._log,
        )

    def run(self) -> None:
        handler = DequeLogHandler(dest=self._log)
        logger = invocation_logger(self.id)
        logger.addHandler(handler)

        cancellation_token = self._cancellation_token

        event_handle: EventHandle = partial(
            self._action.emit_changed_event, self._xthing
        )

        with self._status_lock:
            self._status = InvocationStatus.RUNNING
            self._start_time = datetime.now()
            event_handle(self._status)

        try:
            kwargs = self._input
            if isinstance(kwargs, EmptyInput) or kwargs is None:
                result = self._action.__get__(xthing_obj=self._xthing)(
                    event_handle, cancellation_token, logger
                )
            else:
                result = self._action.__get__(xthing_obj=self._xthing)(
                    kwargs, event_handle, cancellation_token, logger
                )

            with self._status_lock:
                self._status = InvocationStatus.COMPLETED
                self._return_value = result
            event_handle(self._status)
        except InvocationCancelledError as e:
            with self._status_lock:
                self._status = InvocationStatus.CANCELLED
                self._exception = e
            event_handle(self._status)
        except Exception as e:
            logger.error("invocation error")
            with self._status_lock:
                self._status = InvocationStatus.ERROR
                self._exception = e
            event_handle(self._status)
        finally:
            with self._status_lock:
                self._end_time = datetime.now()


class ActionManager:
    def __init__(self):
        self._invocations = {}
        self._invocations_lock = asyncio.Lock()

    async def invoke_action(
        self,
        action: ActionDescriptor,
        xthing: XThing,
        input: Optional[BaseModel],
        id: uuid.UUID,
        cancellation_token: Optional[CancellationToken],
    ):
        invocation = Invocation(action, xthing, input, id, cancellation_token)
        await asyncio.get_running_loop().run_in_executor(
            None, action.emit_changed_event, xthing, InvocationStatus.PENDING
        )

        asyncio.get_running_loop().run_in_executor(None, invocation.run)
        async with self._invocations_lock:
            self._invocations[str(invocation.id).lower()] = invocation
        return invocation

    async def list_invocation(
        self, action: Optional[ActionDescriptor] = None, xthing: Optional[XThing] = None
    ):
        async with self._invocations_lock:
            return [
                i.response()
                for i in self._invocations.values()
                if xthing is None or i.xthing == xthing
                if action is None or i.action == action
            ]

    def attach_to_app(self, app: FastAPI) -> Self:
        @app.get("/invocations", response_model=list[InvocationModel])
        async def list_all_invocations(request: Request):
            return await self.list_invocation(action=None, xthing=None)

        @app.get("/invocations/{id}", response_model=InvocationModel)
        async def action_invocation(id: uuid.UUID, request: Request):
            try:
                async with self._invocations_lock:
                    return self._invocations[str(id).lower()].response(request=request)
            except KeyError:
                raise HTTPException(
                    status_code=404, detail="No action invocation found with ID {id}"
                )

        @app.delete("/invocations/{id}")
        async def delete_invocation(id: uuid.UUID):
            async with self._invocations_lock:
                invocation = self._invocations[str(id).lower()]
                invocation.cancel()

        return self
