import logging
import json
import time
from uuid import UUID
from datetime import datetime
from queue import Empty
from typing import Any, List
from pydantic import BaseModel

import websockets

from peacasso.datamodel import GeneratorConfig

from .colors import GRAY, GREEN, BLUE, ERROR, NC, WARNING, BOLD

logging.basicConfig(format="%(asctime)s %(message)s", level=logging.INFO)


class WsData(BaseModel):
    id: UUID
    prompt_uuid: UUID
    prompt_config: GeneratorConfig = None
    created_at: datetime
    website: str
    image_url: str = None


class WsResponse(BaseModel):
    errors: List[str]
    data: WsData = None
    action: str
    response_status: int
    request_id: Any = None


class WsMessage(BaseModel):
    message: str


class WsAuthResponse(BaseModel):
    errors: List[str]
    data: WsMessage
    action: str
    response_status: int
    request_id: Any = None


class WebsocketHandler:
    def __init__(
        self, websocket, token, request_queue, shared_queue, max_reconnect=50
    ):
        self._ws = websocket
        self._token = token
        self._request_queue = request_queue
        self._shared_queue = shared_queue
        self._reconnections = 0
        self._max_reconnect = max_reconnect

    async def login(self):
        ws_request = {
            "action": "login",
            "request_id": time.time(),
            "token": self._token,
        }
        try:
            await self._ws.send(json.dumps(ws_request))
            message = await self._ws.recv()
            ws_response = WsAuthResponse(**json.loads(message))
            if ws_response.response_status != 200:
                logging.warning(f"{WARNING}%s{NC}", ws_response.data.message)
                return False
            logging.info(f"{GREEN}Login OK{NC}")
        except json.JSONDecodeError as exc:
            logging.warning(
                f"{WARNING}Invalid JSON data:{NC} %s %s",
                str(exc),
                message_json,
            )
            return False
        except TypeError as exc:
            logging.warning(f"{WARNING}Invalid data format:{NC} %s", str(exc))
            return False
        except KeyboardInterrupt:
            return False
        except websockets.exceptions.ConnectionClosed as exc:
            logging.warning(
                f"{WARNING}Connection Closed:{NC} %s",
                str(exc),
            )
            return False
        except Exception as exc:
            logging.warning(
                f"{WARNING}An error occurs during image generate:{NC} %s",
                str(exc),
            )
            return False
        return True

    def handle_action(self, action, response):
        method = getattr(self, action, None)
        if method:
            method(response.data)
        else:
            logging.debug(
                f"{BLUE}Unknown action:{NC} %s",
                action
            )

    def handle_response(self, response):
        self.handle_action(response.action, response)

    async def communicate(self):
        try:
            message = await self._ws.recv()
            ws_response = WsResponse(**json.loads(message))
            self.handle_response(ws_response)
        except json.JSONDecodeError as exc:
            logging.warning(
                f"{WARNING}Invalid JSON data:{NC} %s %s",
                str(exc),
                message_json,
            )
        except TypeError as exc:
            logging.warning(f"{WARNING}Invalid data format:{NC} %s", str(exc))
        except KeyboardInterrupt:
            raise KeyboardInterrupt
        except websockets.exceptions.ConnectionClosed as exc:
            logging.warning(
                f"{WARNING}Connection Closed:{NC} %s",
                str(exc),
            )
            raise exc
        except Exception as exc:
            logging.warning(
                f"{WARNING}An error occurs during image generate:{NC} %s\n%s",
                str(exc),
                message,
            )

    def create(self, data):
        if data and data.image_url is None:
            self._request_queue.put(data)

    def update(self, data):
        if data and data.image_url is None:
            self._request_queue.put(data)

    def clearqueue(self, data):
        self._request_queue.clear()
        try:
            while True:
                self._shared_queue.get_nowait()
        except Empty:
            pass
