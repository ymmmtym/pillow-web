from io import BytesIO

import requests
from PIL import Image, ImageDraw, ImageFont

MAX_IMAGE_SIZE = 4096
MAX_BACKGROUND_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB


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
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > MAX_BACKGROUND_IMAGE_SIZE:
                raise ValueError("背景画像のサイズが大きすぎます（最大10MB）")
            content = b""
            for chunk in response.iter_content(chunk_size=8192):
                content += chunk
                if len(content) > MAX_BACKGROUND_IMAGE_SIZE:
                    raise ValueError("背景画像のサイズが大きすぎます（最大10MB）")
            image = Image.open(BytesIO(content)).convert(mode)
            image = image.resize((width, height))
        except ValueError:
            raise
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
