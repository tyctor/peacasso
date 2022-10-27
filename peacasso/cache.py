import os
import uuid
from dataclasses import field, asdict
from random import seed
from typing import Any, List, Optional, Union
from pydantic.dataclasses import dataclass
from functools import wraps


@dataclass
class CacheConfig:
    """Configuration for a cache"""

    prompt: str
    num_images: int = 1
    mode: str = "prompt"   # prompt, image, mask
    height: Optional[int] = 512
    width: Optional[int] = 512
    num_inference_steps: Optional[int] = 50
    guidance_scale: Optional[float] = 7.5
    eta: Optional[float] = 0.0
    output_type: Optional[str] = "pil"
    strength: float = 0.8
    seed: Optional[int] = None
    return_intermediates: bool = False
    mask_image: Any = None
    attention_slice: Optional[Union[str, int]] = None
    image_width: Optional[int] = 512
    image_height: Optional[int] = 512

    def get_cache_key(self):
        return str(uuid.uuid5(uuid.NAMESPACE_OID, str(self)))


class FileCache:
    def __init__(self, path: str = os.environ.get("PEACASSO_CACHE_DIR")):
        self.path = path or "cache"

    def _get_path_from_key(self, key: str):
        return os.path.join(self.path, key[:8])

    def _get_data(self, prompt_config):
        data = asdict(prompt_config)
        if isinstance(data["prompt"], (list, tuple)):
            data["prompt"] = " ".join(data["prompt"])
        return data
    
    def get(self, prompt_config):
        data = self._get_data(prompt_config)
        key = CacheConfig(**data).get_cache_key()
        cache_path = os.path.join(self._get_path_from_key(key), key)
        if os.path.exists(cache_path):
            return open(cache_path, "rb")
        return None

    def set(self, prompt_config, content):
        data = self._get_data(prompt_config)
        key = CacheConfig(**data).get_cache_key()
        cache_path = self._get_path_from_key(key)
        os.makedirs(cache_path, exist_ok=True)
        cache_file = os.path.join(cache_path, key)
        with open(cache_file, "wb") as file:
            file.write(content)


cache = FileCache()

#0fd97754-3380-5bd7-aed6-432488198065
#0fd97754-3380-5bd7-aed6-432488198065
