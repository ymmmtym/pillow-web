import sys
from io import BytesIO
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
import requests
from flask.testing import FlaskClient
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from main import MAX_IMAGE_SIZE, app  # noqa: E402
from pillow_web.image import clear_cache
from pillow_web.validation import validate_background_image_url


@pytest.fixture
def client() -> Generator[FlaskClient, None, None]:
    app.testing = True
    with app.test_client() as client:
        yield client


def test_images_png_default(client: FlaskClient) -> None:
    rv = client.get("/test")
    assert rv.status_code == 200
    assert rv.headers["Content-Type"] == "image/png"


def test_images_png_explicit(client: FlaskClient) -> None:
    rv = client.get("/test?format=png")
    assert rv.status_code == 200
    assert rv.headers["Content-Type"] == "image/png"


def test_images_jpg(client: FlaskClient) -> None:
    rv = client.get("/test?format=jpg")
    assert rv.status_code == 200
    assert rv.headers["Content-Type"] == "image/jpeg"


def test_images_jpeg(client: FlaskClient) -> None:
    rv = client.get("/test?format=jpeg")
    assert rv.status_code == 200
    assert rv.headers["Content-Type"] == "image/jpeg"


def test_invalid_format(client: FlaskClient) -> None:
    rv = client.get("/test?format=gif")
    assert rv.status_code == 400


# SSRF validation tests


def test_validate_url_private_ipv4_loopback() -> None:
    with pytest.raises(ValueError, match="プライベートネットワーク"):
        validate_background_image_url("http://127.0.0.1:5000/image.jpg")


def test_validate_url_private_ipv4_10() -> None:
    with pytest.raises(ValueError, match="プライベートネットワーク"):
        validate_background_image_url("http://10.0.0.1/image.jpg")


def test_validate_url_private_ipv4_172() -> None:
    with pytest.raises(ValueError, match="プライベートネットワーク"):
        validate_background_image_url("http://172.16.0.1/image.jpg")


def test_validate_url_private_ipv4_192() -> None:
    with pytest.raises(ValueError, match="プライベートネットワーク"):
        validate_background_image_url("http://192.168.1.1/image.jpg")


def test_validate_url_private_ipv6_loopback() -> None:
    with pytest.raises(ValueError, match="プライベートネットワーク"):
        validate_background_image_url("http://[::1]:5000/image.jpg")


def test_validate_url_invalid_scheme_file() -> None:
    with pytest.raises(ValueError, match="httpもしくはhttps"):
        validate_background_image_url("file:///etc/passwd")


def test_validate_url_invalid_scheme_ftp() -> None:
    with pytest.raises(ValueError, match="httpもしくはhttps"):
        validate_background_image_url("ftp://example.com/image.jpg")


def test_validate_url_no_hostname() -> None:
    with pytest.raises(ValueError, match="ホスト名"):
        validate_background_image_url("http:///image.jpg")


def test_validate_url_public_ip_allowed() -> None:
    validate_background_image_url("http://8.8.8.8/image.jpg")


def test_validate_url_public_domain_allowed() -> None:
    validate_background_image_url("https://example.com/image.jpg")


def test_backgroundimage_private_ip_blocked(client: FlaskClient) -> None:
    rv = client.get("/test?backgroundimage=http://127.0.0.1:5000/image.jpg")
    assert rv.status_code == 400
    assert "プライベートネットワーク" in rv.data.decode()


def test_backgroundimage_invalid_scheme_blocked(client: FlaskClient) -> None:
    rv = client.get("/test?backgroundimage=file:///etc/passwd")
    assert rv.status_code == 400
    assert "httpもしくはhttps" in rv.data.decode()


def test_width_zero(client: FlaskClient) -> None:
    rv = client.get("/test?width=0")
    assert rv.status_code == 400


def test_width_negative(client: FlaskClient) -> None:
    rv = client.get("/test?width=-1")
    assert rv.status_code == 400


def test_width_too_large(client: FlaskClient) -> None:
    rv = client.get("/test?width=99999")
    assert rv.status_code == 400


def test_height_zero(client: FlaskClient) -> None:
    rv = client.get("/test?height=0")
    assert rv.status_code == 400


def test_height_negative(client: FlaskClient) -> None:
    rv = client.get("/test?height=-1")
    assert rv.status_code == 400


def test_height_too_large(client: FlaskClient) -> None:
    rv = client.get("/test?height=99999")
    assert rv.status_code == 400


def test_max_size_boundary(client: FlaskClient) -> None:
    rv = client.get("/test?width=4096&height=4096")
    assert rv.status_code == 200


def test_transparent_background(client: FlaskClient) -> None:
    rv = client.get("/test?mode=RGBA&color=transparent")
    assert rv.status_code == 200
    assert rv.headers["Content-Type"] == "image/png"


<<<<<<< HEAD
def test_backgroundimage_success(client: FlaskClient) -> None:
||||||| 7b0f5ce
def test_backgroundimage_success(client):
=======
def test_backgroundimage_success(client):
    clear_cache()
>>>>>>> origin/main
    img = Image.new("RGB", (100, 100), (255, 0, 0))
    buf = BytesIO()
    img.save(buf, "PNG")
    content = buf.getvalue()

    mock_response = MagicMock()
    mock_response.content = content
    mock_response.raise_for_status.return_value = None

    with patch("pillow_web.image.requests.get", return_value=mock_response):
        rv = client.get("/test?backgroundimage=http://example.com/img.png")
        assert rv.status_code == 200
        assert rv.headers["Content-Type"] == "image/png"


<<<<<<< HEAD
def test_backgroundimage_fetch_failure(client: FlaskClient) -> None:
    with patch(
        "pillow_web.image.requests.get", side_effect=requests.exceptions.ConnectionError("Connection error")
    ):
||||||| 7b0f5ce
def test_backgroundimage_fetch_failure(client):
    with patch("pillow_web.image.requests.get", side_effect=requests.exceptions.ConnectionError("Connection error")):
=======
def test_backgroundimage_fetch_failure(client):
    clear_cache()
    with patch(
        "pillow_web.image.requests.get", side_effect=requests.exceptions.ConnectionError("Connection error")
    ):
>>>>>>> origin/main
        rv = client.get("/test?backgroundimage=http://example.com/img.png")
        assert rv.status_code == 400
        assert "背景画像の読み込みに失敗" in rv.data.decode()


def test_invalid_width_non_numeric(client: FlaskClient) -> None:
    rv = client.get("/test?width=abc")
    assert rv.status_code == 400


def test_invalid_height_non_numeric(client: FlaskClient) -> None:
    rv = client.get("/test?height=abc")
    assert rv.status_code == 400


def test_invalid_spacing_non_numeric(client: FlaskClient) -> None:
    rv = client.get("/test?spacing=abc")
    assert rv.status_code == 400


def test_invalid_font_size_non_numeric(client: FlaskClient) -> None:
    rv = client.get("/test?font_size=abc")
    assert rv.status_code == 400


def test_width_exceeds_max_with_message(client: FlaskClient) -> None:
    rv = client.get(f"/test?width={MAX_IMAGE_SIZE + 1}")
    assert rv.status_code == 400
    assert "must not exceed" in rv.data.decode()


def test_height_exceeds_max_with_message(client: FlaskClient) -> None:
    rv = client.get(f"/test?height={MAX_IMAGE_SIZE + 1}")
    assert rv.status_code == 400
    assert "must not exceed" in rv.data.decode()


def test_japanese_text(client):
    rv = client.get("/%E6%97%A5%E6%9C%AC%E8%AA%9E")  # /日本語
    assert rv.status_code == 200
    assert rv.headers["Content-Type"] == "image/png"


def test_japanese_text_with_custom_size(client):
    rv = client.get("/%E6%97%A5%E6%9C%AC%E8%AA%9E?width=400&height=150&font_size=30")
    assert rv.status_code == 200
    assert rv.headers["Content-Type"] == "image/png"


def test_japanese_text_fallback_handles_error(client):
    from pillow_web.image import _load_font

    with patch("pillow_web.image._font_candidates_init", False), patch(
        "pillow_web.image._FONT_CANDIDATES", ["/nonexistent/font.ttf"]
    ):
        _load_font.cache_clear()
        rv = client.get("/%E6%97%A5%E6%9C%AC%E8%AA%9E")
        assert rv.status_code == 200


def test_font_path_validation_rejects_path_traversal():
    from pillow_web.image import _validate_font_path

    # Valid paths
    assert _validate_font_path("/usr/share/fonts/font.ttf") is True
    assert _validate_font_path("fonts/NotoSans.otf") is True
    assert _validate_font_path("fonts/Font.TTC") is True  # Mixed case
    assert _validate_font_path("releases.v2..ttf") is True  # Double dot in filename

    # Path traversal attempts
    assert _validate_font_path("../../../etc/passwd") is False
    assert _validate_font_path("/path/../../../etc/passwd") is False
    assert _validate_font_path("../abc/def/../font.ttf") is False

    # Tilde expansion
    assert _validate_font_path("~/fonts/font.ttf") is False

    # Invalid extensions
    assert _validate_font_path("/usr/share/fonts/font.txt") is False
    assert _validate_font_path("") is False



# Edge case: large font_size
def test_large_font_size(client: FlaskClient) -> None:
    rv = client.get("/test?font_size=500")
    assert rv.status_code == 200
    assert rv.headers["Content-Type"] == "image/png"


def test_huge_font_size(client: FlaskClient) -> None:
    rv = client.get("/test?font_size=99999")
    assert rv.status_code == 200
    assert rv.headers["Content-Type"] == "image/png"


# Edge case: special characters
def test_emoji_text(client: FlaskClient) -> None:
    rv = client.get("/%F0%9F%98%80")
    assert rv.status_code == 200
    assert rv.headers["Content-Type"] == "image/png"


def test_control_characters(client: FlaskClient) -> None:
    rv = client.get("/test%00%01%02")
    assert rv.status_code == 200
    assert rv.headers["Content-Type"] == "image/png"


def test_unicode_text(client: FlaskClient) -> None:
    rv = client.get("/%E3%83%86%E3%82%B9%E3%83%88")
    assert rv.status_code == 200
    assert rv.headers["Content-Type"] == "image/png"


# Edge case: extreme aspect ratios
def test_extreme_aspect_ratio_wide(client: FlaskClient) -> None:
    rv = client.get("/test?width=4096&height=1")
    assert rv.status_code == 200
    assert rv.headers["Content-Type"] == "image/png"


def test_extreme_aspect_ratio_tall(client: FlaskClient) -> None:
    rv = client.get("/test?width=1&height=4096")
    assert rv.status_code == 200
    assert rv.headers["Content-Type"] == "image/png"


# Integration tests: verify generated image content
def test_image_has_correct_dimensions(client: FlaskClient) -> None:
    rv = client.get("/test?width=300&height=150")
    assert rv.status_code == 200
    img = Image.open(BytesIO(rv.data))
    assert img.size == (300, 150)


def test_image_png_format_valid(client: FlaskClient) -> None:
    rv = client.get("/test")
    assert rv.status_code == 200
    img = Image.open(BytesIO(rv.data))
    assert img.format == "PNG"


def test_image_jpg_format_valid(client: FlaskClient) -> None:
    rv = client.get("/test?format=jpg")
    assert rv.status_code == 200
    img = Image.open(BytesIO(rv.data))
    assert img.format == "JPEG"


def test_image_rgba_transparent(client: FlaskClient) -> None:
    rv = client.get("/test?mode=RGBA&color=transparent")
    assert rv.status_code == 200
    img = Image.open(BytesIO(rv.data))
    assert img.mode == "RGBA"
    # Top-left corner should be fully transparent
    assert img.getpixel((0, 0))[3] == 0


def test_text_alignment_left(client: FlaskClient) -> None:
    rv = client.get("/test?align=left")
    assert rv.status_code == 200
    assert rv.headers["Content-Type"] == "image/png"


def test_text_alignment_right(client: FlaskClient) -> None:
    rv = client.get("/test?align=right")
    assert rv.status_code == 200
    assert rv.headers["Content-Type"] == "image/png"


def test_custom_spacing(client: FlaskClient) -> None:
    rv = client.get("/test?spacing=20")
    assert rv.status_code == 200
    assert rv.headers["Content-Type"] == "image/png"


def test_root_route(client: FlaskClient) -> None:
    rv = client.get("/")
    assert rv.status_code == 200
    assert rv.headers["Content-Type"].startswith("text/html")


def test_docs_route(client: FlaskClient) -> None:
    rv = client.get("/docs")
    assert rv.status_code == 200
    assert rv.headers["Content-Type"].startswith("text/html")
    assert "swagger-ui" in rv.data.decode()


def test_openapi_yaml(client: FlaskClient) -> None:
    rv = client.get("/openapi.yaml")
    assert rv.status_code == 200
    assert rv.headers["Content-Type"].startswith("text/yaml")
