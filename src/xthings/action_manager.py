from __future__ import annotations
from fastapi import FastAPI, Request
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict
from typing import Optional, Any, TypeVar, Generic
from typing import TYPE_CHECKING
from typing_extensions import Self
import uuid
from threading import Thread, RLock
from pydantic import RootModel

if TYPE_CHECKING:  # pragma: no cover
    from .descriptors import ActionDescriptor
    from .xthing import XThing


class InvocationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ERROR = "error"


InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


class InvocationModel(BaseModel, Generic[InputT, OutputT]):
    status: InvocationStatus
    id: uuid.UUID
    action: str
    href: str
    timeStarted: Optional[datetime]
    timeRequested: Optional[datetime]
    timeCompleted: Optional[datetime]
    input: InputT
    output: OutputT


class EmptyObject(BaseModel):
    model_config = ConfigDict(extra="allow")


class EmptyInput(RootModel):
    root: Optional[EmptyObject] = None


class Invocation(Thread):
    def __init__(
        self,
        action: ActionDescriptor,
        xthing: XThing,
        input: Optional[BaseModel] = None,
        id: Optional[uuid.UUID] = None,
    ):
        Thread.__init__(self, daemon=True)

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

    @property
    def id(self):
        return self._id

    @property
    def input(self) -> Any:
        return self._input

    @property
    def output(self) -> Any:
        with self._status_lock:
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
        )

    def run(self) -> None:
        with self._status_lock:
            self._status = InvocationStatus.RUNNING
            self._start_time = datetime.now()

        try:
            kwargs = self._input
            result = self._action.__get__(xthing_obj=self._xthing)(kwargs)

            with self._status_lock:
                self._status = InvocationStatus.COMPLETED
                self._return_value = result
        except Exception as e:
            with self._status_lock:
                self._status = InvocationStatus.ERROR
                self._exception = e
            print(str(e))
        finally:
            with self._status_lock:
                self._end_time = datetime.now()

        return super().run()


class ActionManager:
    def __init__(self):
        self._invocations = {}
        self._invocations_lock = RLock()

    def invoke_action(
        self,
        action: ActionDescriptor,
        xthing: XThing,
        input: Optional[BaseModel],
        id: uuid.UUID,
    ):
        thread = Invocation(action, xthing, input, id)
        with self._invocations_lock:
            self._invocations[str(thread.id)] = thread
        thread.start()
        return thread

    def list_invocation(self):
        return [i.response() for i in self._invocations.values()]

    def attach_to_app(self, app: FastAPI) -> Self:
        @app.get("/invocations", response_model=list[InvocationModel[Any, Any]])
        def list_all_invocations(request: Request):
            return self.list_invocation()

        return self
