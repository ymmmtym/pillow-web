from io import BytesIO

import requests
from PIL import Image, ImageDraw, ImageFont

MAX_IMAGE_SIZE = 4096


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


def _resolve_position(width, height, x=None, y=None, position=None, offset_x=0, offset_y=0):
    anchor = "mm"
    pos_x = width / 2
    pos_y = height / 2

    if position is not None:
        position = position.lower().replace("_", "-")
        if position not in POSITION_MAP:
            valid = ", ".join(sorted(POSITION_MAP))
            raise ValueError(f"無効なpositionです: {position}. 有効な値: {valid}")
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
    x=None,
    y=None,
    position=None,
    offset_x=0,
    offset_y=0,
):
    if background_image_url:
        try:
            response = requests.get(background_image_url, stream=True, timeout=10)
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
        font = ImageFont.truetype("arial.ttf", font_size)
    except OSError:
        font = ImageFont.load_default()

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
