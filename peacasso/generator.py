from dataclasses import asdict
from torch import autocast
from PIL import Image
from typing import List
# from diffusers import StableDiffusionPipeline

import os
import torch
import time

from peacasso.datamodel import GeneratorConfig
from peacasso.pipelines import StableDiffusionPipeline


class ImageGenerator:
    """Generate image from prompt"""

    def __init__(
        self,
        model: str = "CompVis/stable-diffusion-v1-4",
        token: str = os.environ.get("HF_API_TOKEN"),
        cuda_device: int = 0,
    ) -> None:

        assert token is not None, "HF_API_TOKEN environment variable must be set."
        self.device = f"cuda:{cuda_device}" if torch.cuda.is_available() else "cpu"
        self.pipe = StableDiffusionPipeline.from_pretrained(
            model,
            revision="fp16",
            torch_dtype=torch.float16,
            use_auth_token=token,
        ).to(self.device)

    def generate(self, config: GeneratorConfig) -> Image:
        """Generate image from prompt"""
        config.prompt = [config.prompt] * config.num_images
        with autocast("cuda" if torch.cuda.is_available() else "cpu"):
            results = self.pipe(**asdict(config))
        return results

    def list_cuda(self) -> List[int]:
        """List available cuda devices
        Returns:
            List[int]: List of available cuda devices
        """
        available_gpus = [i for i in range(torch.cuda.device_count())]
        return available_gpus


class FakeImageGenerator:
    """
    just for testing without GPU
    """

    def __init__(
        self,
        model: str = "CompVis/stable-diffusion-v1-4",
        token: str = os.environ.get("HF_API_TOKEN"),
        cuda_device: int = 0,
    ) -> None:
        self.cuda_device = cuda_device
        self.device = f"cuda:{cuda_device}"
        self.token = token

    def generate(self, config):
        num_images = config.num_images
        width = config.width
        height = config.height
        images = []
        for _ in range(num_images):
            image = Image.new("RGBA", (width, height), (255, 0, 0))
            images.append(image)
        time.sleep(0.3)
        return dict(images=images)
