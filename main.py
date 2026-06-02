from __future__ import annotations

import logging
import os

from flask import Flask, Response, request, send_file
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from pillow_web.image import MAX_IMAGE_SIZE, generate_image, save_image
from pillow_web.validation import validate_background_image_url

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

__all__ = [
    "app",
    "MAX_IMAGE_SIZE",
]

DEFAULT_WIDTH = 600
DEFAULT_HEIGHT = 200
DEFAULT_MODE = "RGB"
DEFAULT_COLOR = "black"
DEFAULT_FILL = "white"
DEFAULT_ALIGN = "center"
DEFAULT_SPACING = 4
DEFAULT_FONT_SIZE = 120

from flask import Flask, Response, request, send_file

from pillow_web.image import MAX_IMAGE_SIZE, generate_image, save_image
from pillow_web.validation import validate_background_image_url

app = Flask(__name__)
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
)

OPENAPI_SPEC_PATH = os.path.join(os.path.dirname(__file__), "openapi.yaml")


@app.route("/")
@limiter.exempt
def hello() -> str:
    base_url: str = request.host_url
    usage_html: str = f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Pillow Web Image Generation API</title>
        <style>
            body {{ font-family: sans-serif; margin: 2em; line-height: 1.6; }}
            code {{ background-color: #eee; padding: 2px 4px; border-radius: 3px; }}
            h1, h2 {{ color: #333; }}
            ul {{ list-style-type: disc; margin-left: 20px; }}
            li {{ margin-bottom: 0.5em; }}
        </style>
    </head>
    <body>
        <h1>Pillow Web Image Generation API</h1>
        <p>このAPIは、指定されたテキストと様々なオプションで画像を生成します。</p>

        <h2>エンドポイント</h2>
        <p><code>GET /&lt;text&gt;</code></p>
        <p>例: <a href="{base_url}Hello_World"><code>{base_url}Hello_World</code></a></p>
        <p><a href="{base_url}docs"><code>/docs</code></a> でAPIドキュメントを参照できます。</p>

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
            <li><code>format</code> (文字列, デフォルト: png): 出力画像のフォーマット (png, jpg, jpeg)。</li>
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


@app.route("/docs")
def swagger_docs() -> str:
    base_url = request.host_url
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>API Docs - Pillow Web</title>
    <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
        SwaggerUIBundle({{
            url: '{base_url}openapi.yaml',
            dom_id: '#swagger-ui',
        }});
    </script>
</body>
</html>"""


@app.route("/openapi.yaml")
def openapi_spec():
    return send_file(OPENAPI_SPEC_PATH, mimetype="text/yaml")


@app.route("/<text>")
def images(text: str) -> Response | tuple[str, int]:
    logger.info("Request from %s: /%s args=%s", request.remote_addr, text, request.args)
    try:
        width = int(request.args.get("width", DEFAULT_WIDTH))
        height = int(request.args.get("height", DEFAULT_HEIGHT))
        if width <= 0:
            return "width must be greater than 0", 400
        if width > MAX_IMAGE_SIZE:
            return f"width must not exceed {MAX_IMAGE_SIZE}", 400
        if height <= 0:
            return "height must be greater than 0", 400
        if height > MAX_IMAGE_SIZE:
            return f"height must not exceed {MAX_IMAGE_SIZE}", 400

        mode: str = request.args.get("mode", DEFAULT_MODE)
        color_spec: str = request.args.get("color", DEFAULT_COLOR)
        fill: str = request.args.get("fill", DEFAULT_FILL)
        align: str = request.args.get("align", DEFAULT_ALIGN)
        spacing = int(request.args.get("spacing", DEFAULT_SPACING))
        font_size = int(request.args.get("font_size", DEFAULT_FONT_SIZE))
        background_image_url: str | None = request.args.get("backgroundimage")
        x_param = request.args.get("x")
        y_param = request.args.get("y")
        position = request.args.get("position")
        offset_x = int(request.args.get("offset_x", 0))
        offset_y = int(request.args.get("offset_y", 0))
        x = int(x_param) if x_param is not None else None
        y = int(y_param) if y_param is not None else None

        if font_size <= 0:
            return "font_size must be greater than 0", 400
        if spacing < 0:
            return "spacing must not be negative", 400
        if align not in ("left", "center", "right"):
            return "align must be one of: left, center, right", 400
        if mode not in ("RGB", "RGBA"):
            return "mode must be one of: RGB, RGBA", 400

        x_param = request.args.get("x")
        y_param = request.args.get("y")
        position = request.args.get("position")
        offset_x = int(request.args.get("offset_x", 0))
        offset_y = int(request.args.get("offset_y", 0))
        x = int(x_param) if x_param is not None else None
        y = int(y_param) if y_param is not None else None

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
            x=x,
            y=y,
            position=position,
            offset_x=offset_x,
            offset_y=offset_y,
        )

        format_param: str = request.args.get("format", "png").lower()
        if format_param not in ("png", "jpg", "jpeg"):
            return "Unsupported format", 400

        image_io, mimetype = save_image(image, format=format_param)

        return send_file(image_io, mimetype=mimetype)
    except ValueError as e:
        return f"エラーが発生しました: {e}", 400
    except Exception as e:
        return f"予期せぬエラーが発生しました: {e}", 500


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1")
