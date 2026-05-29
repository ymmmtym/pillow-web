from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import requests


MAX_IMAGE_SIZE = 4096


def generate_image(text, width, height, mode='RGB', color='black',
                   fill='white', align='center', spacing=4, font_size=120,
                   background_image_url=None):
    if background_image_url:
        try:
            response = requests.get(background_image_url, stream=True, timeout=10)
            response.raise_for_status()
            image = Image.open(response.raw).convert(mode)
            image = image.resize((width, height))
        except (requests.exceptions.RequestException, IOError) as e:
            raise ValueError(f"背景画像の読み込みに失敗しました: {e}") from e
    else:
        if mode == 'RGBA' and color == 'transparent':
            color = (0, 0, 0, 0)
        image = Image.new(mode, (width, height), color)

    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except IOError:
        font = ImageFont.load_default()

    draw = ImageDraw.Draw(image)
    draw.text((width / 2, height / 2), text, fill=fill, font=font,
              anchor='mm', align=align, spacing=spacing)

    return image


def save_image(image, format='png', quality=70):
    if format in ('jpg', 'jpeg'):
        save_format = 'JPEG'
        mimetype = 'image/jpeg'
    else:
        save_format = 'PNG'
        mimetype = 'image/png'

    image_io = BytesIO()
    image.save(image_io, save_format, quality=quality)
    image_io.seek(0)
    return image_io, mimetype
