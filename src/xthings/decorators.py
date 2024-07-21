from functools import wraps, partial
from pydantic import BaseModel
from typing import Callable, Optional

from .descriptors import PropertyDescriptor, ActionDescriptor


def mark_xthings_property(model: type[BaseModel], func: Callable) -> PropertyDescriptor:
    class PropertyDescriptorSubclass(PropertyDescriptor):
        def __get__(self, obj, objtype=None):
            return super().__get__(obj, objtype)

    descriptor = PropertyDescriptorSubclass(model, None, getter=func)
    return descriptor


@wraps(mark_xthings_property)
def xthings_property(model: type[BaseModel]):
    return partial(mark_xthings_property, model)


def mark_xthings_action(
    input_model: Optional[type[BaseModel]],
    output_model: Optional[type[BaseModel]],
    func: Callable,
):
    class XThingsActionDescriptor(ActionDescriptor):
        pass

    return XThingsActionDescriptor(
        func, input_model=input_model, output_model=output_model
    )


@wraps(mark_xthings_action)
def xthings_action(
    input_model: Optional[type[BaseModel]] = None,
    output_model: Optional[type[BaseModel]] = None,
):
    return partial(mark_xthings_action, input_model, output_model)
