from __future__ import annotations

import logging
import os
import threading
import time
from functools import lru_cache
from io import BytesIO
from pathlib import Path

import qrcode
import requests
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

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


_ERROR_CORRECTION_MAP: dict[str, int] = {
    "L": qrcode.constants.ERROR_CORRECT_L,
    "M": qrcode.constants.ERROR_CORRECT_M,
    "Q": qrcode.constants.ERROR_CORRECT_Q,
    "H": qrcode.constants.ERROR_CORRECT_H,
}

QR_DEFAULT_BOX_SIZE = 10
QR_DEFAULT_ERROR_CORRECTION = "M"


def _generate_qr_code(
    content: str,
    box_size: int = QR_DEFAULT_BOX_SIZE,
    error_correction: str = QR_DEFAULT_ERROR_CORRECTION,
) -> Image.Image:
    ec_level = _ERROR_CORRECTION_MAP.get(error_correction.upper())
    if ec_level is None:
        valid = ", ".join(sorted(_ERROR_CORRECTION_MAP))
        raise ValidationError(f"無効なerror_correctionです: {error_correction}. 有効な値: {valid}")
    qr = qrcode.QRCode(
        version=None,
        error_correction=ec_level,
        box_size=box_size,
        border=4,
    )
    qr.add_data(content)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white").convert("RGBA")


def _resolve_qr_position(
    width: int,
    height: int,
    qr_width: int,
    qr_height: int,
    x: int | None = None,
    y: int | None = None,
    position: str | None = None,
    offset_x: int = 0,
    offset_y: int = 0,
) -> tuple[int, int]:
    pos_x = (width - qr_width) // 2
    pos_y = (height - qr_height) // 2

    if position is not None:
        position = position.lower().replace("_", "-")
        if position not in POSITION_MAP:
            valid = ", ".join(sorted(POSITION_MAP))
            raise ValidationError(f"無効なqr_positionです: {position}. 有効な値: {valid}")

        if position == "top-left":
            pos_x, pos_y = 0, 0
        elif position == "top-center":
            pos_x, pos_y = (width - qr_width) // 2, 0
        elif position == "top-right":
            pos_x, pos_y = width - qr_width, 0
        elif position == "center-left":
            pos_x, pos_y = 0, (height - qr_height) // 2
        elif position == "center":
            pos_x, pos_y = (width - qr_width) // 2, (height - qr_height) // 2
        elif position == "center-right":
            pos_x, pos_y = width - qr_width, (height - qr_height) // 2
        elif position == "bottom-left":
            pos_x, pos_y = 0, height - qr_height
        elif position == "bottom-center":
            pos_x, pos_y = (width - qr_width) // 2, height - qr_height
        elif position == "bottom-right":
            pos_x, pos_y = width - qr_width, height - qr_height

    if x is not None:
        pos_x = x
    if y is not None:
        pos_y = y

    pos_x += offset_x
    pos_y += offset_y

    return int(pos_x), int(pos_y)


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
    filter_type: str | None = None,
    filter_strength: float | None = None,
    qr: str | None = None,
    qr_size: int = QR_DEFAULT_BOX_SIZE,
    qr_error_correction: str = QR_DEFAULT_ERROR_CORRECTION,
    qr_position: str | None = None,
    qr_x: int | None = None,
    qr_y: int | None = None,
    qr_offset_x: int = 0,
    qr_offset_y: int = 0,
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

    draw = ImageDraw.Draw(image)
    draw.text((pos_x, pos_y), text, fill=fill, font=font, anchor=anchor, align=align, spacing=spacing)

    image = apply_filter(image, filter_type, filter_strength)

    if qr:
        if qr_size > QR_MAX_BOX_SIZE:
            raise ValidationError(f"qr_sizeは{QR_MAX_BOX_SIZE}を超えない値を指定してください")
        qr_image = _generate_qr_code(qr, box_size=qr_size, error_correction=qr_error_correction)
        paste_x, paste_y = _resolve_qr_position(
            width,
            height,
            qr_image.width,
            qr_image.height,
            x=qr_x,
            y=qr_y,
            position=qr_position,
            offset_x=qr_offset_x,
            offset_y=qr_offset_y,
        )
        paste_x = max(0, paste_x)
        paste_y = max(0, paste_y)
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        image.paste(qr_image, (paste_x, paste_y), qr_image)
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
