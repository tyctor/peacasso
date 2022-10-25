import asyncio
import base64
import hashlib
import io
import itertools
import json
import logging
import os
import random
import time
import typing as t
from datetime import datetime
from io import BytesIO
from queue import Empty, Queue
from typing import Any, List
from uuid import UUID

import websockets
from PIL.ImageOps import fit
from pydantic import BaseModel

from peacasso.cache import cache
from peacasso.generator import FakeImageGenerator, ImageGenerator
from peacasso.utils import base64_to_pil

GREEN = "\033[92m"
BLUE = "\033[94m"
GRAY = "\033[90m"
NC = "\033[0m"
BOLD = "\033[1m"
WARNING = "\033[93m"

logging.basicConfig(format="%(message)s", level=logging.INFO)

T = t.TypeVar("T")


class OrderedSet(t.MutableSet[T]):
    """A set that preserves insertion order by internally using a dict.
    >>> OrderedSet([1, 2, "foo"])
    """

    __slots__ = ("_d",)

    def __init__(self, iterable: t.Optional[t.Iterable[T]] = None):
        self._d = dict.fromkeys(iterable) if iterable else {}

    def add(self, x: T) -> None:
        self._d[x] = None

    def clear(self) -> None:
        self._d.clear()

    def discard(self, x: T) -> None:
        self._d.pop(x, None)

    def __getitem__(self, index) -> T:
        try:
            return next(itertools.islice(self._d, index, index + 1))
        except StopIteration:
            raise IndexError(f"index {index} out of range")

    def __contains__(self, x: object) -> bool:
        return self._d.__contains__(x)

    def __len__(self) -> int:
        return self._d.__len__()

    def __iter__(self) -> t.Iterator[T]:
        return self._d.__iter__()

    def __str__(self):
        return f"{{{', '.join(str(i) for i in self)}}}"

    def __repr__(self):
        return f"<OrderedSet {self}>"


class GeneratorConfig(BaseModel):
    """Configuration for a generation"""

    prompt: str
    num_images: int = 1
    mode: str = "prompt"  # prompt, image, mask
    height: int | None = 512
    width: int | None = 512
    num_inference_steps: int | None = 20
    guidance_scale: float | None = 7.5
    eta: float | None = 0.0
    # generator: Optional[Any] = None
    output_type: str | None = "pil"
    strength: float = 0.8
    init_image: Any = None
    seed: int | None = None
    return_intermediates: bool = False
    mask_image: Any = None
    attention_slice: str | int | None = None
    image_index: int | None = 0
    image_width: int | None = 512
    image_height: int | None = 512


class WsData(BaseModel):
    id: UUID
    prompt_uuid: UUID
    prompt_config: GeneratorConfig
    created_at: datetime
    website: str
    image_url: str | None


class WsResponse(BaseModel):
    errors: List[str]
    data: WsData
    action: str
    response_status: int
    request_id: Any | None


class WsMessage(BaseModel):
    message: str


class WsAuthResponse(BaseModel):
    errors: List[str]
    data: WsMessage
    action: str
    response_status: int
    request_id: Any | None


def satitize_prompt(prompt):
    return prompt.replace("\n", " ")


class SetQueue(Queue):
    """
    Queue with unique items
    """

    def _init(self, maxsize):
        self.queue = OrderedSet()
        self.items = dict()
        self.current = None

    def _put(self, item):
        # print("_put", item.id,  satitize_prompt(item.prompt_config.prompt[:40]), end=" ")
        if self.current != item.id:
            self.queue.add(item.id)
            self.items[item.id] = item
        #    print("Done")
        # else:
        #    print("Rejected")

    def _get(self):
        self.current = self.queue.pop()
        item = self.items.pop(self.current)
        # print("_get", item.id,  satitize_prompt(item.prompt_config.prompt[:40]))
        return item


# load token from .env variable
hf_token = os.environ.get("HF_API_TOKEN")
if hf_token:
    generator = ImageGenerator(token=hf_token)
else:
    generator = FakeImageGenerator(token=hf_token)


def generate(prompt_config: GeneratorConfig) -> str:
    """Generate an image given some prompt"""
    image = cache.get(prompt_config)
    if image:
        image = io.BytesIO(image.read())
        time.sleep(random.random() * 3)
        logging.info(
            f"{GRAY}Cached prompt: {BOLD}%s...{NC}",
            satitize_prompt(prompt_config.prompt[:40]),
        )
    else:
        if prompt_config.init_image:
            prompt_config.init_image = base64_to_pil(prompt_config.init_image)
        result = None
        result = generator.generate(prompt_config)
        pil_image = result["images"][prompt_config.image_index]
        pil_image = fit(
            pil_image, (prompt_config.image_width, prompt_config.image_height)
        )
        image = io.BytesIO()
        pil_image.save(image, format="PNG")
        pil_image.close()
        cache.set(prompt_config, image.getvalue())
        time.sleep(random.random() * 3)
        logging.info(
            f"{GREEN}Created prompt: {BOLD}%s...{NC}",
            satitize_prompt(prompt_config.prompt[:40]),
        )
    return image


async def consume(queue, websocket):
    logging.info(f"{GREEN}Started queue consumer{NC}")
    while True:
        await asyncio.sleep(0.01)
        try:
            item = queue.get(timeout=0.1)
            image = generate(item.prompt_config)
            ws_request = {
                "action": "update",
                "request_id": time.time(),
                "pk": str(item.id),
                "data": {"image": base64.b64encode(image.getvalue()).decode()},
            }
            await websocket.send(json.dumps(ws_request))
            queue.task_done()
        except Empty:
            continue


async def main(scheme: str, host: str, port: int, path: str, token: str):
    if not token:
        logging.info(f"{WARNING}Empty token, exiting...{NC}")
        return
    url = f"{scheme}://{host}:{port}{path}"
    async with websockets.connect(url) as websocket:
        ws_request = {
            "action": "login",
            "request_id": time.time(),
            "token": token,
        }
        logging.info(f"{GREEN}Connected to websocket on %s{NC}", url)
        await websocket.send(json.dumps(ws_request))
        message = await websocket.recv()
        ws_response = WsAuthResponse(**json.loads(message))
        if ws_response.response_status != 200:
            logging.info(f"{WARNING}%s{NC}", ws_response.data.message)
            return

        queue = SetQueue()
        consumer = asyncio.create_task(consume(queue, websocket))

        while True:
            try:
                message = await websocket.recv()
                ws_response = WsResponse(**json.loads(message))
                # work only on data without assigned image
                if ws_response.data.image_url is None:
                    queue.put(ws_response.data)
            except json.JSONDecodeError as exc:
                logging.info(
                    f"{WARNING}Invalid JSON data:{NC} %s %s",
                    str(exc),
                    message_json,
                )
            except TypeError as exc:
                logging.info(f"{WARNING}Invalid data format:{NC} %s", str(exc))
            except KeyboardInterrupt:
                break
            except Exception as exc:
                logging.info(
                    f"{WARNING}An error occurs during image generate:{NC} %s",
                    str(exc),
                )
        consumer.cancel()
        await asyncio.gather(consumer, return_exceptions=True)
