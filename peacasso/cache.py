import os
import uuid
from dataclasses import field
from random import seed
from typing import Any, List, Optional, Union
from pydantic.dataclasses import dataclass
from functools import wraps


@dataclass
class CacheConfig:
    """Configuration for a cache"""

    prompt: Union[str, List[str]]
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
    
    def get(self, prompt_config):
        data = prompt_config.__dict__
        key = CacheConfig(**data).get_cache_key()
        print(key, prompt_config.__dict__)
        cache_path = os.path.join(self._get_path_from_key(key), key)
        print(cache_path)
        if os.path.exists(cache_path):
            return open(cache_path, "rb")
        return None

    def set(self, prompt_config, content):
        data = prompt_config.__dict__
        data["prompt"] = data["prompt"][0]
        key = CacheConfig(**data).get_cache_key()
        cache_path = self._get_path_from_key(key)
        os.makedirs(cache_path, exist_ok=True)
        cache_file = os.path.join(cache_path, key)
        print(key, prompt_config.__dict__)
        print(cache_path)
        print(cache_file)
        with open(cache_file, "wb") as file:
            file.write(content)


cache = FileCache()

#0fd97754-3380-5bd7-aed6-432488198065
#0fd97754-3380-5bd7-aed6-432488198065
