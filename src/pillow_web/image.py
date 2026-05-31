from __future__ import annotations

from io import BytesIO

import requests
from PIL import Image, ImageDraw, ImageFont

MAX_IMAGE_SIZE = 4096
BACKGROUND_IMAGE_TIMEOUT = 10
DEFAULT_QUALITY = 70


ColorSpec = str | tuple[int, int, int, int]


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
        try:
            response = requests.get(background_image_url, stream=True, timeout=BACKGROUND_IMAGE_TIMEOUT)
            response.raise_for_status()
            image = Image.open(response.raw).convert(mode)
            image = image.resize((width, height))
        except (OSError, requests.exceptions.RequestException) as e:
            raise ValueError(f"背景画像の読み込みに失敗しました: {e}") from e
    else:
        if mode == "RGBA" and color == "transparent":
            color = (0, 0, 0, 0)
        image = Image.new(mode, (width, height), color)

    try:
        font: ImageFont.ImageFont | ImageFont.FreeTypeFont = ImageFont.truetype("arial.ttf", font_size)
    except OSError:
        font = ImageFont.load_default()

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

    image_io = BytesIO()
    image.save(image_io, save_format, quality=quality)
    image_io.seek(0)
    return image_io, mimetype
