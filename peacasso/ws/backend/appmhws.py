import time
import websockets
import json
import base64
from uuid import UUID
from datetime import datetime
from typing import Any, Optional, List
from io import BytesIO
import io
import os
from pydantic.dataclasses import dataclass
from peacasso.generator import ImageGenerator, FakeImageGenerator
from peacasso.cache import cache
from peacasso.datamodel import GeneratorConfig
import hashlib
import time
from PIL.ImageOps import fit

from peacasso.utils import base64_to_pil

# # load token from .env variable
hf_token = os.environ.get("HF_API_TOKEN")
if hf_token:
    generator = ImageGenerator(token=hf_token)
else:
    generator = FakeImageGenerator(token=hf_token)


@dataclass
class WsData:
    id: UUID 
    prompt_uuid: UUID
    prompt_config: GeneratorConfig
    created_at: datetime
    website: str
    image_url: str | None


@dataclass
class WsResponse:
    errors: List[str]
    data: WsData
    action: str
    response_status: int
    request_id: Any | None


def generate(prompt_config: GeneratorConfig) -> str:
    """Generate an image given some prompt"""
    #print(prompt_config.image_index)
    # print(prompt_config.init_image)
    image = cache.get(prompt_config)
    if image:
        print("Cached image")
        image = io.BytesIO(image.read())
    else:
        if prompt_config.init_image:
            prompt_config.init_image = base64_to_pil(prompt_config.init_image)
        result = None
        result = generator.generate(prompt_config)
        pil_image = result["images"][prompt_config.image_index]
        pil_image = fit(pil_image, (prompt_config.image_width, prompt_config.image_height))
        image = io.BytesIO()
        pil_image.save(image, format="PNG")
        pil_image.close()
        cache.set(prompt_config, image.getvalue())
    return image


async def main(scheme: str, host: str, port: int, path: str):
    url = f"{scheme}://{host}:{port}{path}"
    print(f"Connecting to websocket on {url}")
    async with websockets.connect(url) as websocket:
        while True:
            try:
                message = await websocket.recv()
                print(f"Got message {message}")
                ws_response = WsResponse(**json.loads(message))
                # work only on data without assigned image
                if ws_response.data.image_url is None:
                    image = generate(ws_response.data.prompt_config)
                    ws_request = {
                        "action": "update",
                        "request_id": time.time(), 
                        "pk": str(ws_response.data.id),
                        "data": {
                            "image": base64.b64encode(image.getvalue()).decode()
                        }
                    }
                    print(f"Created image for GeneratedImage({ws_response.data.id})")
                    await websocket.send(json.dumps(ws_request))
            except json.JSONDecodeError as exc:
                print("Invalid JSON data:", str(exc), message_json)
            except TypeError as exc:
                print("Invalid data format:", str(exc))
            except Exception as exc:
                print("An error occurs during image generate:", str(exc))
