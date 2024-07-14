"""
Handle notification events, property and actionstatus change via websocket
"""

from __future__ import annotations
from anyio import create_memory_object_stream, create_task_group
from anyio.abc import ObjectReceiveStream, ObjectSendStream
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from json import JSONDecodeError
import logging
from typing import TYPE_CHECKING


if TYPE_CHECKING:  # pragma: no cover
    from .xthing import XThing


async def send_message_to_websocket(
    websocket: WebSocket, receive_stream: ObjectReceiveStream
):
    """Send objects from a stream to a websocket"""
    async with receive_stream:
        async for item in receive_stream:
            await websocket.send_json(jsonable_encoder(item))


async def receive_message_from_websocket(
    websocket: WebSocket, send_stream: ObjectSendStream, xthing: XThing
):
    """Receive and relay message received from a websocket"""
    while True:
        try:
            data = await websocket.receive_json()
            result = dispatch_message(data, send_stream, xthing)
            await websocket.send_json(jsonable_encoder(result))
        except WebSocketDisconnect:
            await send_stream.aclose()
            return
        except JSONDecodeError:
            await websocket.send_json(
                jsonable_encoder(
                    {"status": "error", "errorMessage": "JSONDecoderError"}
                )
            )


def dispatch_message(data, send_stream: ObjectSendStream, xthing: XThing):
    try:
        # TODO: will distinguish property observer and action observer
        if data["messageType"] == "addPropertyObservation":
            for key in data["data"].keys():
                xthing.add_observer_by_attr(key, send_stream)
        elif data["messageType"] == "addActionObservation":
            for key in data["data"].keys():
                xthing.add_observer_by_attr(key, send_stream)
        else:
            raise ValueError(
                "messageType must be 'addPropertyObservation' or 'addActionObservation'"
            )
        return {"status": "success"}
    except KeyError as e:
        logging.error(f"Got a bad websocket message: {data}, caused KeyError {e}")
        return {"status": "error", "errorMessage": "BadKey"}
    except ValueError as e:
        logging.error(f"Got a bad value for 'messateType' caused ValueError {e}")
        return {"status": "error", "errorMessage": "Bad messateType value"}
    except AttributeError as e:
        logging.error(f"Got a bad websocket message: {data} caused AttributeError {e}")
        return {"status": "error", "errorMessage": "BadAttribute"}


async def websocket_endpoint(xthing: XThing, websocket: WebSocket):
    """Handle communication to a client via websocket"""
    await websocket.accept()
    send_stream, receive_stream = create_memory_object_stream[dict]()

    async with create_task_group() as tg:
        tg.start_soon(send_message_to_websocket, websocket, receive_stream)
        tg.start_soon(receive_message_from_websocket, websocket, send_stream, xthing)
