from __future__ import annotations

import logging
import os
import threading
import time
from functools import lru_cache
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image, ImageColor, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from pillow_web.exceptions import BackgroundImageError, ValidationError
from pillow_web.validation import validate_background_image_url

logger = logging.getLogger(__name__)

MAX_IMAGE_SIZE = 4096
MAX_BACKGROUND_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB
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
    if not path:
        return False
    if path.startswith("~"):
        return False
    normalized = os.path.normpath(path)
    if normalized.startswith("..") or "/.." in normalized:
        return False
    if not path.lower().endswith((".ttf", ".otf", ".ttc")):
        return False
    return True


def _init_font_candidates() -> None:
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
    _init_font_candidates()
    for path in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, font_size)
        except OSError:
            continue
    return ImageFont.load_default()


POSITION_MAP = {
    "top-left": ("la", 0, 0),
    "top-center": ("ma", 0, 0),
    "top-right": ("ra", 0, 0),
    "center-left": ("lm", 0, 0),
    "center": ("mm", 0, 0),
    "center-right": ("rm", 0, 0),
    "bottom-left": ("ld", 0, 0),
    "bottom-center": ("md", 0, 0),
    "bottom-right": ("rd", 0, 0),
}


VALID_FILTERS = frozenset(
    {
        "blur",
        "sepia",
        "grayscale",
        "brightness",
        "contour",
        "emboss",
        "sharpen",
        "smooth",
        "edge_enhance",
    }
)

FILTER_DEFAULT_STRENGTH: dict[str, float] = {
    "blur": 5.0,
    "brightness": 1.5,
    "sepia": 1.0,
}


def _apply_sepia(image: Image.Image, strength: float = 1.0) -> Image.Image:
    if image.mode == "RGBA":
        alpha = image.split()[3]
        rgb = image.convert("RGB")
    else:
        rgb = image

    gray = rgb.convert("L")
    g = gray.point(lambda i: int(i * 0.88))
    b = gray.point(lambda i: int(i * 0.54))
    sepia = Image.merge("RGB", (gray, g, b))

    blend_ratio = min(strength, 1.0)
    sepia = Image.blend(rgb, sepia, blend_ratio)

    if image.mode == "RGBA":
        sepia = Image.merge("RGBA", (*sepia.split(), alpha))

    return sepia


def apply_filter(
    image: Image.Image,
    filter_type: str | None,
    filter_strength: float | None = None,
) -> Image.Image:
    if filter_type is None:
        return image

    if filter_type == "blur":
        radius = filter_strength if filter_strength is not None else FILTER_DEFAULT_STRENGTH["blur"]
        return image.filter(ImageFilter.GaussianBlur(radius=radius))
    elif filter_type == "grayscale":
        if image.mode == "RGBA":
            alpha = image.split()[3]
            gray = image.convert("L").convert("RGB")
            result = Image.merge("RGBA", (*gray.split(), alpha))
            return result
        return image.convert("L").convert(image.mode)
    elif filter_type == "sepia":
        s = filter_strength if filter_strength is not None else FILTER_DEFAULT_STRENGTH["sepia"]
        return _apply_sepia(image, s)
    elif filter_type == "brightness":
        factor = filter_strength if filter_strength is not None else FILTER_DEFAULT_STRENGTH["brightness"]
        enhancer = ImageEnhance.Brightness(image)
        return enhancer.enhance(factor)
    elif filter_type == "contour":
        return image.filter(ImageFilter.CONTOUR)
    elif filter_type == "emboss":
        return image.filter(ImageFilter.EMBOSS)
    elif filter_type == "sharpen":
        return image.filter(ImageFilter.SHARPEN)
    elif filter_type == "smooth":
        return image.filter(ImageFilter.SMOOTH)
    elif filter_type == "edge_enhance":
        return image.filter(ImageFilter.EDGE_ENHANCE)
    else:
        raise ValidationError(f"無効なフィルターです: {filter_type}")


def _resolve_position(
    width: int,
    height: int,
    x: int | None = None,
    y: int | None = None,
    position: str | None = None,
    offset_x: int = 0,
    offset_y: int = 0,
) -> tuple[float, float, str]:
    anchor = "mm"
    pos_x = width / 2
    pos_y = height / 2

    if position is not None:
        position = position.lower().replace("_", "-")
        if position not in POSITION_MAP:
            valid = ", ".join(sorted(POSITION_MAP))
            raise ValidationError(f"無効なpositionです: {position}. 有効な値: {valid}")
        anchor, _, _ = POSITION_MAP[position]

    if position == "top-left":
        pos_x, pos_y = 0, 0
    elif position == "top-center":
        pos_x, pos_y = width / 2, 0
    elif position == "top-right":
        pos_x, pos_y = width, 0
    elif position == "center-left":
        pos_x, pos_y = 0, height / 2
    elif position == "center":
        pos_x, pos_y = width / 2, height / 2
    elif position == "center-right":
        pos_x, pos_y = width, height / 2
    elif position == "bottom-left":
        pos_x, pos_y = 0, height
    elif position == "bottom-center":
        pos_x, pos_y = width / 2, height
    elif position == "bottom-right":
        pos_x, pos_y = width, height

    if x is not None:
        pos_x = x
    if y is not None:
        pos_y = y

    pos_x += offset_x
    pos_y += offset_y

    return pos_x, pos_y, anchor


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


def _apply_gradient_to_layer(layer: Image.Image, gradient_from: str, gradient_to: str) -> Image.Image:
    try:
        c1 = ImageColor.getrgb(gradient_from)
        c2 = ImageColor.getrgb(gradient_to)
    except ValueError as e:
        raise ValidationError(f"色の指定が無効です: {e}") from e
    alpha = layer.split()[3]
    h = layer.height

    strip_l = Image.linear_gradient("L").resize((1, h), Image.Resampling.BILINEAR)
    strip_rgba = Image.new("RGBA", (1, h))
    px_in = strip_l.load()
    px_out = strip_rgba.load()
    assert px_in is not None
    assert px_out is not None
    for y in range(h):
        t = px_in[0, y] / 255.0  # type: ignore[operator]
        r = int(c1[0] + (c2[0] - c1[0]) * t)
        g = int(c1[1] + (c2[1] - c1[1]) * t)
        b = int(c1[2] + (c2[2] - c1[2]) * t)
        px_out[0, y] = (r, g, b, 255)

    gradient = strip_rgba.resize((layer.width, h), Image.Resampling.BILINEAR)
    gradient.putalpha(alpha)
    return gradient


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
    x: int | None = None,
    y: int | None = None,
    position: str | None = None,
    offset_x: int = 0,
    offset_y: int = 0,
    shadow_color: str | None = None,
    shadow_offset_x: int = 3,
    shadow_offset_y: int = 3,
    stroke_width: int = 0,
    stroke_color: str = "black",
    gradient_from: str | None = None,
    gradient_to: str | None = None,
    rotation: float = 0,
    filter_type: str | None = None,
    filter_strength: float | None = None,
) -> Image.Image:
    if background_image_url:
        cached = _get_cached_background_image(background_image_url, mode, width, height)
        if cached is not None:
            image = cached
        else:
            try:
                validate_background_image_url(background_image_url)
                response = requests.get(
                    background_image_url,
                    timeout=BACKGROUND_IMAGE_TIMEOUT,
                )
                response.raise_for_status()
                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > MAX_BACKGROUND_IMAGE_SIZE:
                    raise BackgroundImageError("背景画像のサイズが大きすぎます（最大10 MB）")
                data = b""
                for chunk in response.iter_content(chunk_size=8192):
                    data += chunk
                    if len(data) > MAX_BACKGROUND_IMAGE_SIZE:
                        raise BackgroundImageError("背景画像のサイズが大きすぎます（最大10 MB）")
                _set_cached_background_image(background_image_url, data)
                image = Image.open(BytesIO(data)).convert(mode)
                image = image.resize((width, height))
            except ValidationError:
                raise
            except BackgroundImageError:
                raise
            except (OSError, requests.exceptions.RequestException) as e:
                logger.error("背景画像の取得に失敗: url=%s, error=%s", background_image_url, e)
                raise BackgroundImageError(f"背景画像の読み込みに失敗しました: {e}") from e
    else:
        if mode == "RGBA" and color == "transparent":
            color = (0, 0, 0, 0)
        image = Image.new(mode, (width, height), color)

    font = _load_font(font_size)

    pos_x, pos_y, anchor = _resolve_position(
        width,
        height,
        x=x,
        y=y,
        position=position,
        offset_x=offset_x,
        offset_y=offset_y,
    )

    has_gradient = gradient_from is not None and gradient_to is not None
    if (gradient_from is not None) != (gradient_to is not None):
        raise ValidationError("gradient_fromとgradient_toは両方指定する必要があります")
    needs_layer = rotation != 0 or has_gradient

    if needs_layer:
        text_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(text_layer)
        try:
            fill_rgba = ImageColor.getrgb(fill)
        except ValueError as e:
            raise ValidationError(f"文字色(fill)の指定が無効です: {e}") from e
        try:
            stroke_rgba = ImageColor.getrgb(stroke_color)
        except ValueError as e:
            raise ValidationError(f"縁取り色(stroke_color)の指定が無効です: {e}") from e
        draw.text(
            (pos_x, pos_y),
            text,
            fill=fill_rgba,
            font=font,
            anchor=anchor,
            align=align,
            spacing=spacing,
            stroke_width=stroke_width,
            stroke_fill=stroke_rgba,
        )

        if has_gradient:
            alpha_channel = text_layer.split()[3]
            if stroke_width > 0:
                kernel_size = stroke_width * 2 + 1
                fill_alpha = alpha_channel.filter(ImageFilter.MinFilter(kernel_size))
            else:
                fill_alpha = alpha_channel
            assert gradient_from is not None
            assert gradient_to is not None
            gradient_layer = _apply_gradient_to_layer(text_layer, gradient_from, gradient_to)
            text_layer = Image.composite(gradient_layer, text_layer, fill_alpha)

        if rotation:
            text_layer = text_layer.rotate(
                rotation,
                expand=False,
                center=(pos_x, pos_y),
                fillcolor=(0, 0, 0, 0),
            )

        if image.mode != "RGBA":
            image = image.convert("RGBA")

        if shadow_color is not None:
            shadow_mask = text_layer.split()[3]
            try:
                parsed_shadow = ImageColor.getrgb(shadow_color)
            except ValueError as e:
                raise ValidationError(f"影の色の指定が無効です: {e}") from e
            shadow_img = Image.new("RGBA", (width, height), parsed_shadow[:3] + (255,))
            shadow_img.putalpha(shadow_mask)
            shadow_offset = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            shadow_offset.paste(shadow_img, (shadow_offset_x, shadow_offset_y), shadow_img)
            image = Image.alpha_composite(image, shadow_offset)

        image = Image.alpha_composite(image, text_layer)
    else:
        draw = ImageDraw.Draw(image)
        try:
            fill_rgba = ImageColor.getrgb(fill)
        except ValueError as e:
            raise ValidationError(f"文字色(fill)の指定が無効です: {e}") from e
        try:
            stroke_rgba = ImageColor.getrgb(stroke_color)
        except ValueError as e:
            raise ValidationError(f"縁取り色(stroke_color)の指定が無効です: {e}") from e
        if shadow_color is not None:
            try:
                shadow_rgba = ImageColor.getrgb(shadow_color)
            except ValueError as e:
                raise ValidationError(f"影の色の指定が無効です: {e}") from e
            draw.text(
                (pos_x + shadow_offset_x, pos_y + shadow_offset_y),
                text,
                fill=shadow_rgba,
                font=font,
                anchor=anchor,
                align=align,
                spacing=spacing,
                stroke_width=stroke_width,
                stroke_fill=shadow_rgba,
            )
        draw.text(
            (pos_x, pos_y),
            text,
            fill=fill_rgba,
            font=font,
            anchor=anchor,
            align=align,
            spacing=spacing,
            stroke_width=stroke_width,
            stroke_fill=stroke_rgba,
        )

    image = apply_filter(image, filter_type, filter_strength)

    return image


_FORMAT_MAP: dict[str, tuple[str, str]] = {
    "png": ("PNG", "image/png"),
    "jpg": ("JPEG", "image/jpeg"),
    "jpeg": ("JPEG", "image/jpeg"),
    "webp": ("WEBP", "image/webp"),
    "avif": ("AVIF", "image/avif"),
}


def save_image(
    image: Image.Image,
    format: str = "png",
    quality: int = DEFAULT_QUALITY,
) -> tuple[BytesIO, str]:
    save_format, mimetype = _FORMAT_MAP.get(format, ("PNG", "image/png"))

    if save_format == "JPEG" and image.mode in ("RGBA", "P"):
        image = image.convert("RGB")

    image_io = BytesIO()
    image.save(image_io, save_format, quality=quality)
    image_io.seek(0)
    return image_io, mimetype
