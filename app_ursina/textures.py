from __future__ import annotations
import os
from ursina.texture import Texture
from pathlib import Path
from ursina import load_texture
from app_ursina.config import TEXTURE_DIR

def load_texture_file(filename: str) -> Texture | None:
    """Load a texture from TEXTURE_DIR by filename, or None if it is absent."""
    if not os.path.exists(path=os.path.join(TEXTURE_DIR,
                                            filename)):
        return None
    return load_texture(name=os.path.splitext(filename)[0],
                        folder=Path(TEXTURE_DIR))

def load_body_texture(texture: str | None) -> Texture | None:
    """The loaded surface texture for a body, or None if it has none."""
    return load_texture_file(filename=texture) if texture is not None else None
