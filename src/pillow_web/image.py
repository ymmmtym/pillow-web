import os
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import requests


MAX_IMAGE_SIZE = 4096

_FONT_CANDIDATES: list[str] = []


def _validate_font_path(path: str) -> bool:
    """Validate font path to prevent path traversal attacks."""
    if not path:
        return False
    # Reject paths with path traversal patterns
    if ".." in path or path.startswith("~"):
        return False
    # Only allow common font extensions
    allowed_extensions = (".ttf", ".otf", ".ttc", ".TTF", ".OTF", ".TTC")
    if not path.endswith(allowed_extensions):
        return False
    return True


def _init_font_candidates() -> None:
    if _FONT_CANDIDATES:
        return

    env_font = os.environ.get("PILLOW_WEB_FONT_PATH")
    if env_font and _validate_font_path(env_font):
        _FONT_CANDIDATES.append(env_font)

    _FONT_CANDIDATES.extend(
        [
            "fonts/NotoSansJP-Regular.otf",
            "fonts/NotoSansJP-Regular.ttf",
            "fonts/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansJP-Regular.otf",
            "/usr/share/fonts/truetype/noto/NotoSansJP-Regular.ttf",
            "arial.ttf",
        ]
    )


def _load_font(font_size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    _init_font_candidates()
    for path in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, font_size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


def generate_image(
    text,
    width,
    height,
    mode="RGB",
    color="black",
    fill="white",
    align="center",
    spacing=4,
    font_size=120,
    background_image_url=None,
):
    if background_image_url:
        try:
            response = requests.get(background_image_url, stream=True, timeout=10)
            response.raise_for_status()
            image = Image.open(response.raw).convert(mode)
            image = image.resize((width, height))
        except (requests.exceptions.RequestException, IOError) as e:
            raise ValueError(f"背景画像の読み込みに失敗しました: {e}") from e
    else:
        if mode == "RGBA" and color == "transparent":
            color = (0, 0, 0, 0)
        image = Image.new(mode, (width, height), color)

    font = _load_font(font_size)

    draw = ImageDraw.Draw(image)
    draw.text((width / 2, height / 2), text, fill=fill, font=font, anchor="mm", align=align, spacing=spacing)

    return image


def save_image(image, format="png", quality=70):
    if format in ("jpg", "jpeg"):
        save_format = "JPEG"
        mimetype = "image/jpeg"
    else:
        save_format = "PNG"
        mimetype = "image/png"

    image_io = BytesIO()
    image.save(image_io, save_format, quality=quality)
    image_io.seek(0)
    return image_io, mimetype
