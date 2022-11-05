import asyncio
import json
import logging
import time
from queue import Empty
from typing import List
import multiprocessing as mp

import websockets

from peacasso.cache import cache
from peacasso.generator import FakeImageGenerator, ImageGenerator

from .colors import GRAY, GREEN, BLUE, ERROR, NC, WARNING, BOLD
from .consumer import consumer
from .queue import SetQueue
from .websocket import WebsocketHandler


logging.basicConfig(format="%(asctime)s %(message)s", level=logging.INFO)


async def consume_request(request_queue, shared_queue):
    logging.info(f"{GREEN}Started request consumer{NC}")
    while True:
        await asyncio.sleep(0.01)
        try:
            item = request_queue.get(timeout=0.01)
            shared_queue.put(item)
            request_queue.task_done()
        except Empty:
            continue
        except KeyboardInterrupt:
            break


async def consume_response(websocket, response_queue):
    logging.info(f"{GREEN}Started response consumer{NC}")
    while True:
        await asyncio.sleep(0.01)
        try:
            item = response_queue.get(timeout=0.01)
            await websocket.send(json.dumps(item))
        except Empty:
            continue
        except KeyboardInterrupt:
            break


async def main(
    scheme: str,
    host: str,
    port: int,
    path: str,
    token: str,
    cuda_device: List[int],
    max_reconnect: int = 30,
):
    if not token:
        logging.error(f"{ERROR}Empty token, exiting...{NC}")
        return

    request_queue = SetQueue()
    shared_queue = mp.Queue()
    response_queue = mp.Queue()

    consumers = []
    for dev in cuda_device:
        process = mp.Process(
            target=consumer, args=(shared_queue, response_queue, dev)
        )
        consumers.append(process)
        process.start()

    try:
        url = f"{scheme}://{host}:{port}{path}"
        async for websocket in websockets.connect(url):
            logging.info(f"{GREEN}Connected to websocket on %s{NC}", url)

            handler = WebsocketHandler(
                websocket, token, request_queue, shared_queue, max_reconnect
            )
            if not await handler.login():
                return

            request_queue_consumer = asyncio.create_task(
                consume_request(request_queue, shared_queue)
            )
            response_queue_consumer = asyncio.create_task(
                consume_response(websocket, response_queue)
            )

            while True:
                try:
                    await handler.communicate()
                except KeyboardInterrupt:
                    break
                except websockets.exceptions.ConnectionClosed as exc:
                    break

            request_queue_consumer.cancel()
            await asyncio.gather(
                request_queue_consumer, return_exceptions=True
            )
            response_queue_consumer.cancel()
            await asyncio.gather(
                response_queue_consumer, return_exceptions=True
            )
    except websockets.exceptions.InvalidHandshake as exc:
        logging.warning(
            f"{WARNING}Connection Closed:{NC} %s",
            str(exc),
        )
    logging.warning(
        f"{WARNING}Terminating gpu processes{NC}",
    )
    for process in consumers:
        process.terminate()
