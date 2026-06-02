from __future__ import annotations

import os
import threading
import time
from functools import lru_cache
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

MAX_IMAGE_SIZE = 4096
BACKGROUND_IMAGE_TIMEOUT = 10
DEFAULT_QUALITY = 70
CACHE_TTL = 3600
CACHE_MAX_SIZE = 20

_background_image_cache: dict[str, tuple[float, bytes]] = {}
_cache_lock = threading.Lock()

_FONT_CANDIDATES: list[str] = []
_font_candidates_init = False
_font_candidates_lock = threading.Lock()
_FONTS_DIR = Path(__file__).resolve().parent.parent.parent / "fonts"


ColorSpec = str | tuple[int, int, int, int]


def _validate_font_path(path: str) -> bool:
    """Validate font path to prevent path traversal attacks."""
    if not path:
        return False
    # Reject tilde expansion
    if path.startswith("~"):
        return False
    # Normalize and check for path traversal
    normalized = os.path.normpath(path)
    if normalized.startswith("..") or "/.." in normalized:
        return False
    # Only allow common font extensions (case-insensitive)
    if not path.lower().endswith((".ttf", ".otf", ".ttc")):
        return False
    return True


def _init_font_candidates() -> None:
    """Initialize font candidates list with environment variable and system fonts."""
    global _font_candidates_init
    if _font_candidates_init:
        return
    with _font_candidates_lock:
        if _font_candidates_init:
            return

        env_font = os.environ.get("PILLOW_WEB_FONT_PATH")
        if env_font and _validate_font_path(env_font):
            _FONT_CANDIDATES.append(env_font)

        _FONT_CANDIDATES.extend(
            [
                str(_FONTS_DIR / "NotoSansJP-Regular.otf"),
                str(_FONTS_DIR / "NotoSansJP-Regular.ttf"),
                str(_FONTS_DIR / "NotoSansCJK-Regular.ttc"),
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/opentype/noto/NotoSansJP-Regular.otf",
                "/usr/share/fonts/truetype/noto/NotoSansJP-Regular.ttf",
                "arial.ttf",
            ]
        )
        _font_candidates_init = True


@lru_cache(maxsize=64)
def _load_font(font_size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load font with LRU caching (max 64 sizes) to avoid repeated filesystem probes."""
    _init_font_candidates()
    for path in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, font_size)
        except OSError:
            continue
    return ImageFont.load_default()


def _get_cached_background_image(url: str, mode: str, width: int, height: int) -> Image.Image | None:
    with _cache_lock:
        now = time.time()
        if url in _background_image_cache:
            timestamp, data = _background_image_cache[url]
            if now - timestamp < CACHE_TTL:
                image = Image.open(BytesIO(data)).convert(mode)
                image = image.resize((width, height))
                return image
            else:
                del _background_image_cache[url]

    return None


def _set_cached_background_image(url: str, data: bytes) -> None:
    with _cache_lock:
        if len(_background_image_cache) >= CACHE_MAX_SIZE:
            oldest_url = min(_background_image_cache, key=lambda k: _background_image_cache[k][0])
            del _background_image_cache[oldest_url]
        _background_image_cache[url] = (time.time(), data)


def clear_cache() -> None:
    with _cache_lock:
        _background_image_cache.clear()


def generate_image(
    text: str,
    width: int,
    height: int,
    mode: str = "RGB",
    color: ColorSpec = "black",
    fill: str = "white",
    align: str = "center",
    spacing: int = 4,
    font_size: int = 120,
    background_image_url: str | None = None,
) -> Image.Image:
    if background_image_url:
        cached = _get_cached_background_image(background_image_url, mode, width, height)
        if cached is not None:
            image = cached
        else:
            try:
                response = requests.get(background_image_url, timeout=BACKGROUND_IMAGE_TIMEOUT)
                response.raise_for_status()
                data = response.content
                _set_cached_background_image(background_image_url, data)
                image = Image.open(BytesIO(data)).convert(mode)
                image = image.resize((width, height))
            except (OSError, requests.exceptions.RequestException) as e:
                raise ValueError(f"背景画像の読み込みに失敗しました: {e}") from e
    else:
        if mode == "RGBA" and color == "transparent":
            color = (0, 0, 0, 0)
        image = Image.new(mode, (width, height), color)

    font = _load_font(font_size)

    draw = ImageDraw.Draw(image)
    draw.text(
        (width / 2, height / 2),
        text,
        fill=fill,
        font=font,
        anchor="mm",
        align=align,
        spacing=spacing,
    )

    return image


def save_image(
    image: Image.Image,
    format: str = "png",
    quality: int = DEFAULT_QUALITY,
) -> tuple[BytesIO, str]:
    if format in ("jpg", "jpeg"):
        save_format = "JPEG"
        mimetype = "image/jpeg"
    else:
        save_format = "PNG"
        mimetype = "image/png"

    if save_format == "JPEG" and image.mode in ("RGBA", "P"):
        image = image.convert("RGB")

    image_io = BytesIO()
    image.save(image_io, save_format, quality=quality)
    image_io.seek(0)
    return image_io, mimetype
