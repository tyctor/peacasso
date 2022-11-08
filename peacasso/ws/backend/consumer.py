import base64
import io
import json
import logging
import random
import time
import os

from queue import Empty
from multiprocessing.connection import wait
from PIL.ImageOps import fit
from peacasso.cache import cache
from peacasso.datamodel import GeneratorConfig
from peacasso.generator import FakeImageGenerator, ImageGenerator
from peacasso.utils import base64_to_pil

from .colors import GRAY, GREEN, NC, BOLD


logging.basicConfig(format="%(asctime)s %(message)s", level=logging.INFO)


def satitize_prompt(prompt, length=50):
    prompt = prompt.replace("\n", " ")
    if len(prompt) < length - 3:
        return prompt
    return prompt[: length - 3] + "..."


def generate(generated_image, generator) -> str:
    """Generate an image given some prompt"""
    prompt_config = generated_image.prompt_config
    image = cache.get(prompt_config)
    if image:
        image = io.BytesIO(image.read())
        # time.sleep(random.random() * 3 * generator.cuda_device)
        logging.info(
            f"{GRAY}Prompt: {BOLD}%-50s{NC}{GRAY} Cached %s{NC}",
            satitize_prompt(prompt_config.prompt[:50]),
            generated_image.website,
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
        # time.sleep(random.random() * 3 * generator.cuda_device)
        prompt = prompt_config.prompt
        if isinstance(prompt, (list, tuple)):
            prompt = prompt[0]
        logging.info(
            f"{GREEN}Prompt: {BOLD}%-50s{NC}{GREEN} Created (%s) %s{NC}",
            satitize_prompt(prompt[:50]),
            generator.device,
            generated_image.website,
        )
    return image


def consumer(in_queue, out_queue, cuda_device):
    hf_token = os.environ.get("HF_API_TOKEN")
    if hf_token:
        generator = ImageGenerator(token=hf_token, cuda_device=cuda_device)
    else:
        generator = FakeImageGenerator(token=hf_token, cuda_device=cuda_device)
    logging.info(
        f"{GREEN}Started queue consumer with device %s{NC}", generator.device
    )
    while True:
        try:
            item = in_queue.get()
            image = generate(item, generator)
            ws_request = {
                "action": "update",
                "request_id": time.time(),
                "pk": str(item.id),
                "data": {"image": base64.b64encode(image.getvalue()).decode()},
            }
            out_queue.put(ws_request)
        except Empty:
            continue
        except KeyboardInterrupt:
            break
