from __future__ import annotations

from typing import Tuple, Union

from flask import Flask, Response, request, send_file

from pillow_web.image import MAX_IMAGE_SIZE, generate_image, save_image
from pillow_web.validation import validate_background_image_url

app = Flask(__name__)


@app.route("/")
def hello() -> str:
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


@app.route("/<text>")
def images(text: str) -> Union[Response, Tuple[str, int]]:
    try:
        width = int(request.args.get("width", 600))
        height = int(request.args.get("height", 200))
        if width <= 0:
            return "width must be greater than 0", 400
        if width > MAX_IMAGE_SIZE:
            return f"width must not exceed {MAX_IMAGE_SIZE}", 400
        if height <= 0:
            return "height must be greater than 0", 400
        if height > MAX_IMAGE_SIZE:
            return f"height must not exceed {MAX_IMAGE_SIZE}", 400

        mode = request.args.get("mode", "RGB")
        color_spec = request.args.get("color", "black")
        fill = request.args.get("fill", "white")
        align = request.args.get("align", "center")
        spacing = int(request.args.get("spacing", 4))
        font_size = int(request.args.get("font_size", 120))
        background_image_url = request.args.get("backgroundimage")

        if background_image_url:
            try:
                validate_background_image_url(background_image_url)
            except ValueError as e:
                return str(e), 400

        image = generate_image(
            text,
            width,
            height,
            mode=mode,
            color=color_spec,
            fill=fill,
            align=align,
            spacing=spacing,
            font_size=font_size,
            background_image_url=background_image_url,
        )

        format_param = request.args.get("format", "png").lower()
        if format_param not in ("png", "jpg", "jpeg"):
            return "Unsupported format", 400

        image_io, mimetype = save_image(image, format=format_param)

        return send_file(image_io, mimetype=mimetype)
    except ValueError as e:
        return f"エラーが発生しました: {e}", 400
    except Exception as e:
        return f"予期せぬエラーが発生しました: {e}", 500


if __name__ == "__main__":
    app.run(debug=True)
