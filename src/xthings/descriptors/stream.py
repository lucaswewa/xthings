from __future__ import annotations
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from typing import (
    TYPE_CHECKING,
    Optional,
    Literal,
    Union,
    overload,
)
from typing_extensions import Self
import cv2 as cv

from ..streaming import ImageStreamResponse, ImageStream
from .xthings import XThingsDescriptor

if TYPE_CHECKING:  # pragma: no cover
    from ..xthing import XThing


class ImageStreamDescriptor(XThingsDescriptor):
    def __init__(self, imencode_func, get_content_type_func, **kwargs):
        self.imencode = imencode_func
        self.get_content_type = get_content_type_func
        self._kwargs = kwargs

    def __set_name__(self, owner, name):
        self.name = name

    @overload
    def __get__(self, obj: Literal[None], type=None) -> Self: ...
    @overload
    def __get__(self, obj: XThing, type=None) -> ImageStream: ...

    def __get__(self, obj: Optional[XThing], type=None) -> Union[ImageStream, Self]:
        if obj is None:
            return self
        try:
            return obj.__dict__[self.name]
        except KeyError:
            obj.__dict__[self.name] = ImageStream(
                self.imencode, None, self.get_content_type, **self._kwargs
            )

            return obj.__dict__[self.name]

    async def viewer_page(self) -> HTMLResponse:
        url = self.viewer_url
        return HTMLResponse(f"<html><body><img src='{url}'></body></html>")

    def add_to_app(self, app: FastAPI, xthing: XThing):
        app.get(f"{xthing.path}/{self.name}", response_class=ImageStreamResponse)(
            self.__get__(xthing).image_stream_response
        )

        self.viewer_url = f"{xthing.path}/{self.name}"
        app.get(
            f"{xthing.path}/{self.name}/viewer",
            response_class=HTMLResponse,
        )(self.viewer_page)


class PngImageStreamDescriptor(ImageStreamDescriptor):
    def __init__(self, **kwargs):
        ImageStreamDescriptor.__init__(
            self,
            lambda frame: cv.imencode(".png", frame),
            lambda: b"image/png",
            **kwargs,
        )
