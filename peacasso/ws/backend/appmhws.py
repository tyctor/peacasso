import time
import websockets
import json
import base64
from uuid import UUID
from datetime import datetime
from typing import Any, List
from io import BytesIO
import io
import os
from pydantic import BaseModel
from peacasso.generator import ImageGenerator, FakeImageGenerator
from peacasso.cache import cache
import hashlib
import time
from PIL.ImageOps import fit
import logging

from peacasso.utils import base64_to_pil

GREEN = "\033[92m"
BLUE = "\033[94m"
GRAY = "\033[90m"
NC = "\033[0m"
BOLD = "\033[1m"
WARNING = "\033[93m"

logging.basicConfig(format="%(message)s", level=logging.INFO)

# load token from .env variable
hf_token = os.environ.get("HF_API_TOKEN")
if hf_token:
    generator = ImageGenerator(token=hf_token)
else:
    generator = FakeImageGenerator(token=hf_token)


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


def generate(prompt_config: GeneratorConfig) -> str:
    """Generate an image given some prompt"""
    image = cache.get(prompt_config)
    if image:
        logging.info(
            f"{GRAY}Cached image for prompt: {BOLD}%s...{NC}",
            satitize_prompt(prompt_config.prompt[:40]),
        )
        image = io.BytesIO(image.read())
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
        logging.info(
            f"{GREEN}Created image for prompt: {BOLD}%s...{NC}",
            satitize_prompt(prompt_config.prompt[:40]),
        )
    return image


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
        while True:
            try:
                message = await websocket.recv()
                ws_response = WsResponse(**json.loads(message))
                # work only on data without assigned image
                if ws_response.data.image_url is None:
                    image = generate(ws_response.data.prompt_config)
                    ws_request = {
                        "action": "update",
                        "request_id": time.time(),
                        "pk": str(ws_response.data.id),
                        "data": {
                            "image": base64.b64encode(
                                image.getvalue()
                            ).decode()
                        },
                    }
                    await websocket.send(json.dumps(ws_request))
            except json.JSONDecodeError as exc:
                logging.info(
                    f"{WARNING}Invalid JSON data:{NC} %s %s",
                    str(exc),
                    message_json,
                )
            except TypeError as exc:
                logging.info(f"{WARNING}Invalid data format:{NC} %s", str(exc))
            except Exception as exc:
                logging.info(
                    f"{WARNING}An error occurs during image generate:{NC} %s",
                    str(exc),
                )
