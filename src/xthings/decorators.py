from functools import wraps, partial
from typing import Optional, Callable

from .descriptors import PropertyDescriptor


def mark_xthings_property(func: Callable) -> PropertyDescriptor:
    class PropertyDescriptorSubclass(PropertyDescriptor):
        def __get__(self, obj, objtype=None):
            return super().__get__(obj, objtype)

    descriptor = PropertyDescriptorSubclass(0, getter=func)
    return descriptor


@wraps(mark_xthings_property)
def xthings_property(func: Optional[Callable] = None):
    if func is not None:
        return mark_xthings_property(func)
    else:
        return partial(mark_xthings_property)
