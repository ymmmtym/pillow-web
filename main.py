from __future__ import annotations

import logging
import math
import os

from flask import Flask, Response, request, send_file
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from pillow_web.exceptions import BackgroundImageError, PillowWebError, ValidationError
from pillow_web.image import DEFAULT_QUALITY, MAX_IMAGE_SIZE, QR_MAX_BOX_SIZE, VALID_FILTERS, generate_image, save_image
from pillow_web.validation import validate_background_image_url

FILTERS_WITH_STRENGTH = frozenset({"blur", "brightness", "sepia"})
FILTER_STRENGTH_MAX = 10000

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_WIDTH = 600
DEFAULT_HEIGHT = 200
DEFAULT_MODE = "RGB"
DEFAULT_COLOR = "black"
DEFAULT_FILL = "white"
DEFAULT_ALIGN = "center"
DEFAULT_SPACING = 4
DEFAULT_FONT_SIZE = 120
DEFAULT_QR_SIZE = 10
DEFAULT_QR_ERROR_CORRECTION = "M"


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
            <li><code>format</code> (文字列, デフォルト: png): 出力画像のフォーマット (png, jpg, jpeg, webp, avif)。</li>
            <li><code>quality</code> (整数, デフォルト: 70): 出力画像の品質 (1〜100)。JPEG/WebP/AVIF形式で有効。</li>
            <li><code>filter</code> (文字列): 画像に適用するフィルター効果 (blur, sepia, grayscale, brightness, contour, emboss, sharpen, smooth, edge_enhance)。</li>
            <li><code>filter_strength</code> (数値): フィルターの強度。blurの場合は半径、brightnessの場合は倍率、sepiaの場合はブレンド率（0〜1、1.0を超える値は1.0として扱われます）。</li>
            <li><code>qr</code> (文字列): QRコードにエンコードする文字列。</li>
            <li><code>qr_size</code> (整数, デフォルト: 10): QRコードのモジュールサイズ。</li>
            <li><code>qr_error_correction</code> (文字列, デフォルト: M): QRコードの誤り訂正レベル (L, M, Q, H)。</li>
            <li><code>qr_position</code> (文字列): QRコードの配置位置。</li>
            <li><code>qr_x</code>, <code>qr_y</code> (整数): QRコードの座標。</li>
            <li><code>qr_offset_x</code>, <code>qr_offset_y</code> (整数, デフォルト: 0): QRコードのオフセット。</li>
        </ul>

        <h2>例</h2>
        <ul>
            <li><a href="{base_url}Custom_Size?width=800&height=300"><code>{base_url}Custom_Size?width=800&height=300</code></a></li>
            <li><a href="{base_url}Colorful_Text?color=blue&fill=yellow"><code>{base_url}Colorful_Text?color=blue&fill=yellow</code></a></li>
            <li><a href="{base_url}Large_Font?font_size=150"><code>{base_url}Large_Font?font_size=150</code></a></li>
            <li><a href="{base_url}Transparent_Background?mode=RGBA&color=transparent"><code>{base_url}Transparent_Background?mode=RGBA&color=transparent</code></a></li>
            <li><a href="{base_url}With_Image_Background?backgroundimage=https://p.しのびー.jp/le4Tog.jpg"><code>{base_url}With_Image_Background?backgroundimage=https://p.しのびー.jp/le4Tog.jpg</code></a></li>
            <li><a href="{base_url}Blur_Effect?filter=blur&filter_strength=8"><code>{base_url}Blur_Effect?filter=blur&filter_strength=8</code></a></li>
            <li><a href="{base_url}Sepia_Effect?filter=sepia"><code>{base_url}Sepia_Effect?filter=sepia</code></a></li>
            <li><a href="{base_url}Grayscale_Effect?filter=grayscale"><code>{base_url}Grayscale_Effect?filter=grayscale</code></a></li>
            <li><a href="{base_url}QR_Code_Example?qr=https://example.com&qr_position=bottom-right"><code>{base_url}QR_Code_Example?qr=https://example.com&amp;qr_position=bottom-right</code></a></li>
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
def openapi_spec() -> Response:
    return send_file(OPENAPI_SPEC_PATH, mimetype="text/yaml")


@app.route("/<text>")
def images(text: str) -> Response | tuple[str, int]:
    logger.info("Request from %s: /%s args=%s", request.remote_addr, text, request.args)
    try:
        try:
            width = int(request.args.get("width", DEFAULT_WIDTH))
            height = int(request.args.get("height", DEFAULT_HEIGHT))
        except ValueError:
            raise ValidationError("widthおよびheightには整数を指定してください")
        if width <= 0:
            raise ValidationError("widthは0より大きい値を指定してください")
        if width > MAX_IMAGE_SIZE:
            raise ValidationError(f"widthは{MAX_IMAGE_SIZE}を超えない値を指定してください")
        if height <= 0:
            raise ValidationError("heightは0より大きい値を指定してください")
        if height > MAX_IMAGE_SIZE:
            raise ValidationError(f"heightは{MAX_IMAGE_SIZE}を超えない値を指定してください")

        mode: str = request.args.get("mode", DEFAULT_MODE)
        color_spec: str = request.args.get("color", DEFAULT_COLOR)
        fill: str = request.args.get("fill", DEFAULT_FILL)
        align: str = request.args.get("align", DEFAULT_ALIGN)
        try:
            spacing = int(request.args.get("spacing", DEFAULT_SPACING))
            font_size = int(request.args.get("font_size", DEFAULT_FONT_SIZE))
        except ValueError:
            raise ValidationError("spacingおよびfont_sizeには整数を指定してください")
        background_image_url: str | None = request.args.get("backgroundimage")
        x_param = request.args.get("x")
        y_param = request.args.get("y")
        position = request.args.get("position")
        try:
            offset_x = int(request.args.get("offset_x", 0))
            offset_y = int(request.args.get("offset_y", 0))
            x = int(x_param) if x_param is not None else None
            y = int(y_param) if y_param is not None else None
        except ValueError:
            raise ValidationError("x, y, offset_x, offset_yには整数を指定してください")

        if font_size <= 0:
            raise ValidationError("font_sizeは0より大きい値を指定してください")
        if spacing < 0:
            raise ValidationError("spacingに負の値は指定できません")
        if align not in ("left", "center", "right"):
            raise ValidationError("alignは left, center, right のいずれかを指定してください")
        if mode not in ("RGB", "RGBA"):
            raise ValidationError("modeは RGB または RGBA を指定してください")

        format_param: str = request.args.get("format", "png").lower()
        if format_param not in ("png", "jpg", "jpeg", "webp", "avif"):
            raise ValidationError("formatは png, jpg, jpeg, webp, avif のいずれかを指定してください")

        quality_param = request.args.get("quality")
        try:
            quality = int(quality_param) if quality_param is not None else DEFAULT_QUALITY
        except ValueError:
            raise ValidationError("qualityには整数を指定してください")
        if quality < 1 or quality > 100:
            raise ValidationError("qualityは 1〜100 の範囲で指定してください")

        if background_image_url:
            try:
                validate_background_image_url(background_image_url)
            except ValidationError as e:
                return str(e), 400

        filter_type: str | None = request.args.get("filter")
        if filter_type is not None:
            filter_type = filter_type.lower()
            if filter_type not in VALID_FILTERS:
                valid = ", ".join(sorted(VALID_FILTERS))
                raise ValidationError(f"filterには {valid} のいずれかを指定してください")

        filter_strength_param: str | None = request.args.get("filter_strength")
        filter_strength: float | None = None
        if filter_strength_param is not None:
            if filter_type is None or filter_type not in FILTERS_WITH_STRENGTH:
                valid = ", ".join(sorted(FILTERS_WITH_STRENGTH))
                raise ValidationError(f"filter_strengthは {valid} フィルターでのみ使用できます")
            try:
                filter_strength = float(filter_strength_param)
            except ValueError:
                raise ValidationError("filter_strengthには数値を指定してください")
            if not math.isfinite(filter_strength) or filter_strength <= 0:
                raise ValidationError("filter_strengthは0より大きい有限の値を指定してください")
            if filter_strength > FILTER_STRENGTH_MAX:
                raise ValidationError(f"filter_strengthは{FILTER_STRENGTH_MAX}以下の値を指定してください")

        qr_content: str | None = request.args.get("qr")
        if qr_content is not None and qr_content == "":
            raise ValidationError("qrには空文字列以外を指定してください")
        qr_position = request.args.get("qr_position")
        qr_x_param = request.args.get("qr_x")
        qr_y_param = request.args.get("qr_y")
        try:
            qr_size = int(request.args.get("qr_size", DEFAULT_QR_SIZE))
            qr_offset_x = int(request.args.get("qr_offset_x", 0))
            qr_offset_y = int(request.args.get("qr_offset_y", 0))
            qr_x = int(qr_x_param) if qr_x_param is not None else None
            qr_y = int(qr_y_param) if qr_y_param is not None else None
        except ValueError:
            raise ValidationError("qr_size, qr_offset_x, qr_offset_y, qr_x, qr_yには整数を指定してください")
        qr_error_correction: str = request.args.get("qr_error_correction", DEFAULT_QR_ERROR_CORRECTION)

        if qr_size <= 0:
            raise ValidationError("qr_sizeは0より大きい値を指定してください")
        if qr_size > QR_MAX_BOX_SIZE:
            raise ValidationError(f"qr_sizeは{QR_MAX_BOX_SIZE}を超えない値を指定してください")

        if qr_error_correction not in ("L", "M", "Q", "H"):
            raise ValidationError("qr_error_correctionは L, M, Q, H のいずれかを指定してください")
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
            filter_type=filter_type,
            filter_strength=filter_strength,
            qr=qr_content,
            qr_size=qr_size,
            qr_error_correction=qr_error_correction,
            qr_position=qr_position,
            qr_x=qr_x,
            qr_y=qr_y,
            qr_offset_x=qr_offset_x,
            qr_offset_y=qr_offset_y,
        )

        image_io, mimetype = save_image(image, format=format_param, quality=quality)

        return send_file(image_io, mimetype=mimetype)
    except ValidationError as e:
        logger.warning("バリデーションエラー: %s", e)
        return str(e), 400
    except BackgroundImageError as e:
        logger.error("背景画像エラー: %s", e)
        return str(e), 503
    except PillowWebError as e:
        logger.error("pillow-webエラー: %s", e)
        return str(e), 400
    except Exception as e:
        logger.critical("予期せぬエラー: %s", e, exc_info=True)
        return f"予期せぬエラーが発生しました: {e}", 500


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1")
