from __future__ import annotations
from fastapi import FastAPI, Request, HTTPException
from datetime import datetime
from enum import Enum
import logging
from pydantic import BaseModel, ConfigDict, model_validator
from typing import Optional, Any, Sequence, TypeVar, Generic
from typing import TYPE_CHECKING
from typing_extensions import Self
import uuid
import weakref
from threading import Event, Thread, RLock

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


class Invocation(Thread):
    def __init__(
        self,
        action: ActionDescriptor,
        xthing: XThing,
        input_model: Optional[BaseModel] = None,
        id: Optional[uuid.UUID] = None,
    ):
        Thread.__init__(self, daemon=True)

        self._action = action
        self._xthing = xthing
        self._input_model = input_model
        self._id = id

        self._status_lock = RLock()
        self._status = InvocationStatus.PENDING
        self._return_value = None

    @property
    def id(self):
        return self._id

    def response(self, request: Optional[Request] = None):
        return {"action_id": self.id, "action_status": self._status}

    def run(self) -> None:
        try:
            kwargs = self._input_model
            result = self._action.__get__(xthing_obj=self._xthing)(kwargs)

            with self._status_lock:
                self._status = InvocationStatus.COMPLETED
                self._return_value = result
        except Exception as e:
            print(str(e))

        return super().run()


class ActionManager:
    def __init__(self):
        self._invocations = {}
        self._invocations_lock = RLock()

    def invoke_action(
        self,
        action: ActionDescriptor,
        xthing: XThing,
        input: type[BaseModel],
        id: uuid.UUID,
    ):
        thread = Invocation(action, xthing, input, id)
        with self._invocations_lock:
            self._invocations[str(thread.id)] = thread
        thread.start()
        return thread

    def attach_to_app(self, app: FastAPI) -> Self:
        # TODO: add action related endpoints to the app

        return self
