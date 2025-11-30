from flask import Flask, send_file, request
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import requests

app = Flask(__name__)


@app.route('/')
def hello():
    base_url = request.host_url
    usage_html = f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Pillew Web Image Generation API</title>
        <style>
            body {{ font-family: sans-serif; margin: 2em; line-height: 1.6; }}
            code {{ background-color: #eee; padding: 2px 4px; border-radius: 3px; }}
            h1, h2 {{ color: #333; }}
            ul {{ list-style-type: disc; margin-left: 20px; }}
            li {{ margin-bottom: 0.5em; }}
        </style>
    </head>
    <body>
        <h1>Pillew Web Image Generation API</h1>
        <p>このAPIは、指定されたテキストと様々なオプションで画像を生成します。</p>

        <h2>エンドポイント</h2>
        <p><code>GET /&lt;text&gt;</code></p>
        <p>例: <a href="{base_url}Hello_World"><code>{base_url}Hello_World</code></a></p>

        <h2>クエリパラメータ</h2>
        <ul>
            <li><code>width</code> (整数, デフォルト: 600): 生成する画像の幅。</li>
            <li><code>height</code> (整数, デフォルト: 200): 生成する画像の高さ。</li>
            <li><code>mode</code> (文字列, デフォルト: RGB): 画像のモード (例: RGB, RGBA)。</li>
            <li><code>color</code> (文字列, デフォルト: black): 背景色 (例: red, blue, #FF0000)。
                <ul>
                    <li><code>mode=RGBA</code>の場合、<code>transparent</code>を指定すると透明な背景になります。</li>
                </ul>
            </li>
            <li><code>fill</code> (文字列, デフォルト: white): テキストの色。</li>
            <li><code>align</code> (文字列, デフォルト: center): テキストの配置 (left, center, right)。</li>
            <li><code>spacing</code> (整数, デフォルト: 4): テキストの行間のスペース。</li>
            <li><code>font_size</code> (整数, デフォルト: 120): テキストのフォントサイズ。</li>
            <li><code>backgroundimage</code> (URL): 背景として使用する画像のURL。</li>
        </ul>

        <h2>例</h2>
        <ul>
            <li><a href="{base_url}Custom_Size?width=800&height=300"><code>{base_url}Custom_Size?width=800&height=300</code></a></li>
            <li><a href="{base_url}Colorful_Text?color=blue&fill=yellow"><code>{base_url}Colorful_Text?color=blue&fill=yellow</code></a></li>
            <li><a href="{base_url}Large_Font?font_size=150"><code>{base_url}Large_Font?font_size=150</code></a></li>
            <li><a href="{base_url}Transparent_Background?mode=RGBA&color=transparent"><code>{base_url}Transparent_Background?mode=RGBA&color=transparent</code></a></li>
            <li><a href="{base_url}With_Image_Background?backgroundimage=https://p.しのびー.jp/le4Tog.jpg"><code>{base_url}With_Image_Background?backgroundimage=https://p.しのびー.jp/le4Tog.jpg</code></a></li>
        </ul>
    </body>
    </html>
    """
    return usage_html

@app.route('/<text>')
def images(text):
    try:
        # Image options
        width = int(request.args.get('width', 600))
        height = int(request.args.get('height', 200))
        mode = request.args.get('mode', 'RGB')
        color_spec = request.args.get('color', 'black')
        background_image_url = request.args.get('backgroundimage')

        # Create base image
        if background_image_url:
            try:
                response = requests.get(background_image_url, stream=True)
                response.raise_for_status()
                image = Image.open(response.raw).convert(mode)
                image = image.resize((width, height))
            except (requests.exceptions.RequestException, IOError) as e:
                return f"背景画像の読み込みに失敗しました: {e}", 400
        else:
            if mode == 'RGBA' and color_spec == 'transparent':
                color = (0, 0, 0, 0)
            else:
                color = color_spec
            image = Image.new(mode, (width, height), color)

        # Text options
        fill = request.args.get('fill', 'white')
        align = request.args.get('align', 'center')
        spacing = int(request.args.get('spacing', 4))
        font_size = int(request.args.get('font_size', 120))

        # Font
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except IOError:
            font = ImageFont.load_default()

        draw = ImageDraw.Draw(image)
        draw.text((width / 2, height / 2), text, fill=fill, font=font, anchor='mm', align=align, spacing=spacing)

        format_param = request.args.get('format', 'png').lower()
        if format_param == 'png':
            save_format = 'PNG'
            mimetype = 'image/png'
        elif format_param in ['jpg', 'jpeg']:
            save_format = 'JPEG'
            mimetype = 'image/jpeg'
        else:
            return "Unsupported format", 400

        image_io = BytesIO()
        image.save(image_io, save_format, quality=70)
        image_io.seek(0)

        return send_file(image_io, mimetype=mimetype)
    except ValueError as e:
        return f"エラーが発生しました: {e}", 400
    except Exception as e:
        return f"予期せぬエラーが発生しました: {e}", 500


if __name__ == "__main__":
    app.run(debug=True)
