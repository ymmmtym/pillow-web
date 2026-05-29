from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import requests


def generate_image(
    text,
    width=600,
    height=200,
    mode='RGB',
    color='black',
    background_image_url=None,
    fill='white',
    align='center',
    spacing=4,
    font_size=120,
    format_param='png',
):
    if background_image_url:
        try:
            response = requests.get(background_image_url, stream=True)
            response.raise_for_status()
            image = Image.open(response.raw).convert(mode)
            image = image.resize((width, height))
        except (requests.exceptions.RequestException, OSError) as e:
            raise ValueError(f"背景画像の読み込みに失敗しました: {e}")
    else:
        if mode == 'RGBA' and color == 'transparent':
            color_value = (0, 0, 0, 0)
        else:
            color_value = color
        image = Image.new(mode, (width, height), color_value)

    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except OSError:
        font = ImageFont.load_default()

    draw = ImageDraw.Draw(image)
    draw.text(
        (width / 2, height / 2),
        text,
        fill=fill,
        font=font,
        anchor='mm',
        align=align,
        spacing=spacing,
    )

    format_lower = format_param.lower()
    if format_lower == 'png':
        save_format = 'PNG'
        mimetype = 'image/png'
    elif format_lower in ('jpg', 'jpeg'):
        save_format = 'JPEG'
        mimetype = 'image/jpeg'
    else:
        raise ValueError(f"Unsupported format: {format_param}")

    image_io = BytesIO()
    image.save(image_io, save_format, quality=70)
    image_io.seek(0)

    return image_io, mimetype
