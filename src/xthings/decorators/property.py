from functools import wraps, partial
from pydantic import BaseModel
from typing import Callable

from ..descriptors import PropertyDescriptor, LcrudDescriptor


def create_xproperty_descriptor(
    model: type[BaseModel], func: Callable
) -> PropertyDescriptor:
    class PropertyDescriptorSubclass(PropertyDescriptor):
        def __get__(self, obj, objtype=None):
            return super().__get__(obj, objtype)

    descriptor = PropertyDescriptorSubclass(model, None, getter=func)
    return descriptor


@wraps(create_xproperty_descriptor)
def xproperty(model: type[BaseModel]):
    return partial(create_xproperty_descriptor, model)


def create_xlcrud_descriptor(
    item_model: type[BaseModel], func: Callable
) -> LcrudDescriptor:
    class LcrudDescriptorSubclass(LcrudDescriptor):
        def __get__(self, obj, objtype=None):
            return super().__get__(obj, objtype)

    descriptor = LcrudDescriptorSubclass(item_model, list_func=func)
    return descriptor


@wraps(create_xlcrud_descriptor)
def xlcrud(item_model: type[BaseModel]):
    return partial(create_xlcrud_descriptor, item_model)
