from __future__ import annotations
from fastapi import Body, FastAPI, Request, BackgroundTasks
from functools import partial
from pydantic import BaseModel
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Optional,
    Callable,
    Literal,
    Union,
    overload,
)
import uuid
import pydantic

from ..action import InvocationModel, CancellationToken

from ..utils import pathjoin

from .xthings import XThingsDescriptor

if TYPE_CHECKING:  # pragma: no cover
    from ..xthing import XThing


class ActionDescriptor(XThingsDescriptor):
    def __init__(
        self,
        func: Callable,
        input_model: Optional[type[BaseModel]] = None,
        output_model: Optional[type[BaseModel]] = None,
    ):
        self._func = func
        self._input_model = input_model
        self._output_model = output_model

    def __set_name__(self, owner, name: str):
        self._name = name
        self._invocation_model = pydantic.create_model(
            f"{self.name}_invocation",
            __base__=InvocationModel,
            input=(Optional[self._input_model], None),
            output=(Optional[self.output_model], None),
        )
        self._invocation_model.__name__ = f"{self.name}_invocation"

    @overload
    def __get__(self, xthing_obj: Literal[None], type=None) -> ActionDescriptor: ...

    @overload
    def __get__(self, xthing_obj: XThing, type=None) -> Callable: ...

    def __get__(
        self, xthing_obj: Optional[XThing], type=None
    ) -> Union[ActionDescriptor, Callable]:
        """The function"""
        if xthing_obj is None:
            return self

        return partial(self._func, xthing_obj)

    @property
    def name(self):
        return self._name

    @property
    def input_model(self) -> Optional[type[BaseModel]]:
        return self._input_model

    @property
    def output_model(self) -> Optional[type[BaseModel]]:
        return self._output_model

    def emit_changed_event(self, xthing: XThing, value: Any):
        try:
            runner = xthing._blocking_portal
            if runner is not None:
                runner.start_task_soon(self._emit_changed_event_async, xthing, value)
        except Exception:
            # TODO: handle exception
            ...

    async def _emit_changed_event_async(self, xthing: XThing, value: Any):
        try:
            for observer in xthing.action_observers(self.name):
                await observer.send(
                    {"messageType": "actionStatus", "data": {self.name: value}}
                )
        except Exception:
            # TODO: handle exception
            ...

    def add_to_app(self, app: FastAPI, xthing: XThing):
        async def list_invocations():
            return await xthing.action_manager.list_invocation(self, xthing)

        app.get(pathjoin(xthing.path, self.name))(list_invocations)

        async def start_action(
            request: Request,
            background_tasks: BackgroundTasks,
            body: Optional[Any] = None,
        ):
            # invoke the action in a thread executor
            id = uuid.uuid4()
            action = await xthing._action_manager.invoke_action(
                action=self,
                xthing=xthing,
                input=body,
                id=id,
                cancellation_token=CancellationToken(id),
            )

            return action.response(request=request)

        if self.input_model is not None:
            start_action.__annotations__["body"] = Annotated[self.input_model, Body()]

        app.post(
            pathjoin(xthing.path, self.name),
            response_model=self._invocation_model,
            status_code=201,
        )(start_action)

    def description(self):
        return {}
