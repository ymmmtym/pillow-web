import sys
from collections.abc import Generator
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests
from flask.testing import FlaskClient
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import main as main_module  # noqa: E402
from pillow_web.exceptions import ValidationError
from pillow_web.image import MAX_IMAGE_SIZE, clear_cache
from pillow_web.validation import validate_background_image_url


@pytest.fixture
def client() -> Generator[FlaskClient, None, None]:
    main_module.app.testing = True
    with main_module.app.test_client() as client:
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
    with pytest.raises(ValidationError, match="プライベートネットワーク"):
        validate_background_image_url("http://127.0.0.1:5000/image.jpg")


def test_validate_url_private_ipv4_10() -> None:
    with pytest.raises(ValidationError, match="プライベートネットワーク"):
        validate_background_image_url("http://10.0.0.1/image.jpg")


def test_validate_url_private_ipv4_172() -> None:
    with pytest.raises(ValidationError, match="プライベートネットワーク"):
        validate_background_image_url("http://172.16.0.1/image.jpg")


def test_validate_url_private_ipv4_192() -> None:
    with pytest.raises(ValidationError, match="プライベートネットワーク"):
        validate_background_image_url("http://192.168.1.1/image.jpg")


def test_validate_url_private_ipv6_loopback() -> None:
    with pytest.raises(ValidationError, match="プライベートネットワーク"):
        validate_background_image_url("http://[::1]:5000/image.jpg")


def test_validate_url_invalid_scheme_file() -> None:
    with pytest.raises(ValidationError, match="httpもしくはhttps"):
        validate_background_image_url("file:///etc/passwd")


def test_validate_url_invalid_scheme_ftp() -> None:
    with pytest.raises(ValidationError, match="httpもしくはhttps"):
        validate_background_image_url("ftp://example.com/image.jpg")


def test_validate_url_no_hostname() -> None:
    with pytest.raises(ValidationError, match="ホスト名"):
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


def test_backgroundimage_success(client: FlaskClient) -> None:
    clear_cache()
    img = Image.new("RGB", (100, 100), (255, 0, 0))
    buf = BytesIO()
    img.save(buf, "PNG")
    content = buf.getvalue()

    mock_response = MagicMock()
    mock_response.content = content
    mock_response.headers = {}
    mock_response.iter_content.return_value = [content]
    mock_response.raise_for_status.return_value = None

    with patch("pillow_web.image.requests.get", return_value=mock_response):
        rv = client.get("/test?backgroundimage=http://93.184.216.34/img.png")
        assert rv.status_code == 200
        assert rv.headers["Content-Type"] == "image/png"


def test_backgroundimage_fetch_failure(client: FlaskClient) -> None:
    clear_cache()
    with patch(
        "pillow_web.image.requests.get", side_effect=requests.exceptions.ConnectionError("Connection error")
    ):
        rv = client.get("/test?backgroundimage=http://93.184.216.34/img.png")
        assert rv.status_code == 503
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
    assert "超えない" in rv.data.decode()


def test_height_exceeds_max_with_message(client: FlaskClient) -> None:
    rv = client.get(f"/test?height={MAX_IMAGE_SIZE + 1}")
    assert rv.status_code == 400
    assert "超えない" in rv.data.decode()


# Text position tests


def test_position_top_left(client: FlaskClient) -> None:
    rv = client.get("/test?position=top-left")
    assert rv.status_code == 200


def test_position_top_center(client: FlaskClient) -> None:
    rv = client.get("/test?position=top-center")
    assert rv.status_code == 200


def test_position_top_right(client: FlaskClient) -> None:
    rv = client.get("/test?position=top-right")
    assert rv.status_code == 200


def test_position_center_left(client: FlaskClient) -> None:
    rv = client.get("/test?position=center-left")
    assert rv.status_code == 200


def test_position_center(client: FlaskClient) -> None:
    rv = client.get("/test?position=center")
    assert rv.status_code == 200


def test_position_center_right(client: FlaskClient) -> None:
    rv = client.get("/test?position=center-right")
    assert rv.status_code == 200


def test_position_bottom_left(client: FlaskClient) -> None:
    rv = client.get("/test?position=bottom-left")
    assert rv.status_code == 200


def test_position_bottom_center(client: FlaskClient) -> None:
    rv = client.get("/test?position=bottom-center")
    assert rv.status_code == 200


def test_position_bottom_right(client: FlaskClient) -> None:
    rv = client.get("/test?position=bottom-right")
    assert rv.status_code == 200


def test_position_underscore_variant(client: FlaskClient) -> None:
    rv = client.get("/test?position=bottom_right")
    assert rv.status_code == 200


def test_position_invalid(client: FlaskClient) -> None:
    rv = client.get("/test?position=invalid-position")
    assert rv.status_code == 400


def test_xy_coordinates(client: FlaskClient) -> None:
    rv = client.get("/test?x=100&y=50")
    assert rv.status_code == 200


def test_x_only(client: FlaskClient) -> None:
    rv = client.get("/test?x=100")
    assert rv.status_code == 200


def test_y_only(client: FlaskClient) -> None:
    rv = client.get("/test?y=50")
    assert rv.status_code == 200


def test_xy_non_numeric(client: FlaskClient) -> None:
    rv = client.get("/test?x=abc")
    assert rv.status_code == 400


def test_offset_xy(client: FlaskClient) -> None:
    rv = client.get("/test?offset_x=10&offset_y=20")
    assert rv.status_code == 200


def test_position_with_offset(client: FlaskClient) -> None:
    rv = client.get("/test?position=bottom-right&offset_x=-10&offset_y=-10")
    assert rv.status_code == 200


def test_xy_with_offset(client: FlaskClient) -> None:
    rv = client.get("/test?x=200&y=100&offset_x=5&offset_y=5")
    assert rv.status_code == 200


def test_offset_x_non_numeric(client: FlaskClient) -> None:
    rv = client.get("/test?offset_x=abc")
    assert rv.status_code == 400


def test_offset_y_non_numeric(client: FlaskClient) -> None:
    rv = client.get("/test?offset_y=abc")
    assert rv.status_code == 400


def test_japanese_text(client: FlaskClient) -> None:
    rv = client.get("/%E6%97%A5%E6%9C%AC%E8%AA%9E")  # /日本語
    assert rv.status_code == 200
    assert rv.headers["Content-Type"] == "image/png"


def test_japanese_text_with_custom_size(client: FlaskClient) -> None:
    rv = client.get("/%E6%97%A5%E6%9C%AC%E8%AA%9E?width=400&height=150&font_size=30")
    assert rv.status_code == 200
    assert rv.headers["Content-Type"] == "image/png"


def test_japanese_text_fallback_handles_error(client: FlaskClient) -> None:
    from pillow_web.image import _load_font

    with (
        patch("pillow_web.image._font_candidates_init", False),
        patch("pillow_web.image._FONT_CANDIDATES", ["/nonexistent/font.ttf"]),
    ):
        _load_font.cache_clear()
        rv = client.get("/%E6%97%A5%E6%9C%AC%E8%AA%9E")
        assert rv.status_code == 200


def test_font_path_validation_rejects_path_traversal() -> None:
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


def test_image_webp_format_valid(client: FlaskClient) -> None:
    rv = client.get("/test?format=webp")
    assert rv.status_code == 200
    assert rv.headers["Content-Type"] == "image/webp"
    img = Image.open(BytesIO(rv.data))
    assert img.format == "WEBP"


def test_image_avif_format_valid(client: FlaskClient) -> None:
    rv = client.get("/test?format=avif")
    assert rv.status_code == 200
    assert rv.headers["Content-Type"] == "image/avif"
    img = Image.open(BytesIO(rv.data))
    assert img.format == "AVIF"


def test_image_webp_with_quality(client: FlaskClient) -> None:
    rv = client.get("/test?format=webp&quality=90")
    assert rv.status_code == 200
    assert rv.headers["Content-Type"] == "image/webp"


def test_image_avif_with_quality(client: FlaskClient) -> None:
    rv = client.get("/test?format=avif&quality=50")
    assert rv.status_code == 200
    assert rv.headers["Content-Type"] == "image/avif"


def test_quality_default(client: FlaskClient) -> None:
    rv = client.get("/test?format=jpg")
    assert rv.status_code == 200


def test_quality_explicit(client: FlaskClient) -> None:
    rv = client.get("/test?format=jpg&quality=80")
    assert rv.status_code == 200


def test_quality_too_low(client: FlaskClient) -> None:
    rv = client.get("/test?quality=0")
    assert rv.status_code == 400


def test_quality_negative(client: FlaskClient) -> None:
    rv = client.get("/test?quality=-1")
    assert rv.status_code == 400


def test_quality_too_high(client: FlaskClient) -> None:
    rv = client.get("/test?quality=101")
    assert rv.status_code == 400


def test_quality_non_numeric(client: FlaskClient) -> None:
    rv = client.get("/test?quality=abc")
    assert rv.status_code == 400


def test_unsupported_format_webp_invalid(client: FlaskClient) -> None:
    rv = client.get("/test?format=gif")
    assert rv.status_code == 400


def test_webp_with_rgba(client: FlaskClient) -> None:
    rv = client.get("/test?format=webp&mode=RGBA&color=transparent")
    assert rv.status_code == 200
    assert rv.headers["Content-Type"] == "image/webp"


def test_image_rgba_transparent(client: FlaskClient) -> None:
    rv = client.get("/test?mode=RGBA&color=transparent")
    assert rv.status_code == 200
    img = Image.open(BytesIO(rv.data))
    assert img.mode == "RGBA"
    # Top-left corner should be fully transparent
    pixel = img.getpixel((0, 0))
    assert isinstance(pixel, tuple)
    assert pixel[3] == 0


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


def test_font_size_zero(client: FlaskClient) -> None:
    rv = client.get("/test?font_size=0")
    assert rv.status_code == 400


def test_font_size_negative(client: FlaskClient) -> None:
    rv = client.get("/test?font_size=-1")
    assert rv.status_code == 400


def test_spacing_negative(client: FlaskClient) -> None:
    rv = client.get("/test?spacing=-1")
    assert rv.status_code == 400


def test_invalid_align(client: FlaskClient) -> None:
    rv = client.get("/test?align=top")
    assert rv.status_code == 400


def test_invalid_mode(client: FlaskClient) -> None:
    rv = client.get("/test?mode=CMYK")
    assert rv.status_code == 400


def test_backgroundimage_size_limit_content_length(client: FlaskClient) -> None:
    clear_cache()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Length": f"{11 * 1024 * 1024}"}
    mock_response.iter_content.return_value = [b"x" * 11 * 1024 * 1024]
    mock_response.__enter__.return_value = mock_response
    with patch("pillow_web.image.requests.get", return_value=mock_response):
        rv = client.get("/test?backgroundimage=http://93.184.216.34/img.png")
        assert rv.status_code == 503


def test_backgroundimage_size_limit_stream(client: FlaskClient) -> None:
    clear_cache()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {}
    mock_response.iter_content.return_value = [b"x" * (11 * 1024 * 1024)]
    mock_response.__enter__.return_value = mock_response
    with patch("pillow_web.image.requests.get", return_value=mock_response):
        rv = client.get("/test?backgroundimage=http://93.184.216.34/img.png")
        assert rv.status_code == 503


# Text effects tests


def test_shadow_color(client: FlaskClient) -> None:
    rv = client.get("/test?shadow_color=gray")
    assert rv.status_code == 200
    assert rv.headers["Content-Type"] == "image/png"


def test_shadow_with_offset(client: FlaskClient) -> None:
    rv = client.get("/test?shadow_color=gray&shadow_offset_x=5&shadow_offset_y=5")
    assert rv.status_code == 200


def test_shadow_offset_non_numeric(client: FlaskClient) -> None:
    rv = client.get("/test?shadow_color=gray&shadow_offset_x=abc")
    assert rv.status_code == 400


def test_stroke_width(client: FlaskClient) -> None:
    rv = client.get("/test?stroke_width=3")
    assert rv.status_code == 200


def test_stroke_with_color(client: FlaskClient) -> None:
    rv = client.get("/test?stroke_width=3&stroke_color=red")
    assert rv.status_code == 200


def test_stroke_width_non_numeric(client: FlaskClient) -> None:
    rv = client.get("/test?stroke_width=abc")
    assert rv.status_code == 400


def test_stroke_width_negative(client: FlaskClient) -> None:
    rv = client.get("/test?stroke_width=-1")
    assert rv.status_code == 400


def test_gradient_text(client: FlaskClient) -> None:
    rv = client.get("/test?gradient_from=red&gradient_to=blue")
    assert rv.status_code == 200


def test_gradient_only_from(client: FlaskClient) -> None:
    rv = client.get("/test?gradient_from=red")
    assert rv.status_code == 400


def test_gradient_only_to(client: FlaskClient) -> None:
    rv = client.get("/test?gradient_to=blue")
    assert rv.status_code == 400


def test_rotation(client: FlaskClient) -> None:
    rv = client.get("/test?rotation=45")
    assert rv.status_code == 200


def test_rotation_negative(client: FlaskClient) -> None:
    rv = client.get("/test?rotation=-10")
    assert rv.status_code == 200


def test_rotation_non_numeric(client: FlaskClient) -> None:
    rv = client.get("/test?rotation=abc")
    assert rv.status_code == 400


def test_effects_combo_shadow_stroke(client: FlaskClient) -> None:
    rv = client.get("/test?shadow_color=gray&stroke_width=2&stroke_color=red")
    assert rv.status_code == 200


def test_effects_combo_gradient_rotation(client: FlaskClient) -> None:
    rv = client.get("/test?gradient_from=yellow&gradient_to=green&rotation=30")
    assert rv.status_code == 200


def test_shadow_with_rgba(client: FlaskClient) -> None:
    rv = client.get("/test?mode=RGBA&color=transparent&shadow_color=gray")
    assert rv.status_code == 200


def test_gradient_with_stroke(client: FlaskClient) -> None:
    rv = client.get("/test?gradient_from=red&gradient_to=blue&stroke_width=2&stroke_color=black")
    assert rv.status_code == 200


def test_rotation_with_shadow(client: FlaskClient) -> None:
    rv = client.get("/test?rotation=15&shadow_color=gray")
    assert rv.status_code == 200


def test_shadow_color_invalid(client: FlaskClient) -> None:
    rv = client.get("/test?shadow_color=notacolor")
    assert rv.status_code == 400


def test_stroke_color_invalid(client: FlaskClient) -> None:
    rv = client.get("/test?stroke_width=3&stroke_color=nonexistent")
    assert rv.status_code == 400


def test_gradient_from_invalid(client: FlaskClient) -> None:
    rv = client.get("/test?gradient_from=xyz&gradient_to=blue")
    assert rv.status_code == 400


def test_gradient_to_invalid(client: FlaskClient) -> None:
    rv = client.get("/test?gradient_from=red&gradient_to=notacolor")
    assert rv.status_code == 400


def test_shadow_offset_negative(client: FlaskClient) -> None:
    rv = client.get("/test?shadow_color=gray&shadow_offset_x=-5&shadow_offset_y=-5")
    assert rv.status_code == 200


def test_rotation_with_position(client: FlaskClient) -> None:
    rv = client.get("/test?rotation=45&position=bottom-right")
    assert rv.status_code == 200


def test_all_effects_combined(client: FlaskClient) -> None:
    rv = client.get(
        "/test?shadow_color=gray&stroke_width=2&stroke_color=red"
        "&gradient_from=yellow&gradient_to=green&rotation=30"
    )
    assert rv.status_code == 200


def test_shadow_with_alpha_hex_color(client: FlaskClient) -> None:
    rv = client.get("/test?shadow_color=%2300000080")
    assert rv.status_code == 200


def test_gradient_with_alpha_hex_colors(client: FlaskClient) -> None:
    rv = client.get("/test?gradient_from=%23FF000080&gradient_to=%230000FF80")
    assert rv.status_code == 200


def test_stroke_color_invalid_via_layer_path(client: FlaskClient) -> None:
    rv = client.get("/test?stroke_width=3&stroke_color=invalid&rotation=10")
    assert rv.status_code == 400


def test_shadow_offset_exceeds_width(client: FlaskClient) -> None:
    rv = client.get("/test?shadow_color=gray&shadow_offset_x=9999")
    assert rv.status_code == 400


def test_shadow_offset_exceeds_height(client: FlaskClient) -> None:
    rv = client.get("/test?shadow_color=gray&shadow_offset_y=9999")
    assert rv.status_code == 400


def test_shadow_offset_negative_exceeds_width(client: FlaskClient) -> None:
    rv = client.get("/test?shadow_color=gray&shadow_offset_x=-9999")
    assert rv.status_code == 400


def test_shadow_offset_at_boundary(client: FlaskClient) -> None:
    rv = client.get("/test?shadow_color=gray&shadow_offset_x=600&shadow_offset_y=200")
    assert rv.status_code == 200


def test_shadow_offset_negative_boundary(client: FlaskClient) -> None:
    rv = client.get("/test?shadow_color=gray&shadow_offset_x=-600&shadow_offset_y=-200")
    assert rv.status_code == 200


# Filter tests


def test_filter_blur(client: FlaskClient) -> None:
    rv = client.get("/test?filter=blur&filter_strength=5")
    assert rv.status_code == 200
    assert rv.headers["Content-Type"] == "image/png"


def test_filter_blur_default_strength(client: FlaskClient) -> None:
    rv = client.get("/test?filter=blur")
    assert rv.status_code == 200


def test_filter_grayscale(client: FlaskClient) -> None:
    rv = client.get("/test?filter=grayscale")
    assert rv.status_code == 200


def test_filter_sepia(client: FlaskClient) -> None:
    rv = client.get("/test?filter=sepia")
    assert rv.status_code == 200


def test_filter_sepia_with_strength(client: FlaskClient) -> None:
    rv = client.get("/test?filter=sepia&filter_strength=0.5")
    assert rv.status_code == 200


def test_filter_brightness(client: FlaskClient) -> None:
    rv = client.get("/test?filter=brightness&filter_strength=1.2")
    assert rv.status_code == 200


def test_filter_brightness_default_strength(client: FlaskClient) -> None:
    rv = client.get("/test?filter=brightness")
    assert rv.status_code == 200


def test_filter_contour(client: FlaskClient) -> None:
    rv = client.get("/test?filter=contour")
    assert rv.status_code == 200


def test_filter_emboss(client: FlaskClient) -> None:
    rv = client.get("/test?filter=emboss")
    assert rv.status_code == 200


def test_filter_sharpen(client: FlaskClient) -> None:
    rv = client.get("/test?filter=sharpen")
    assert rv.status_code == 200


def test_filter_smooth(client: FlaskClient) -> None:
    rv = client.get("/test?filter=smooth")
    assert rv.status_code == 200


def test_filter_edge_enhance(client: FlaskClient) -> None:
    rv = client.get("/test?filter=edge_enhance")
    assert rv.status_code == 200


def test_filter_invalid(client: FlaskClient) -> None:
    rv = client.get("/test?filter=invalid")
    assert rv.status_code == 400


def test_filter_strength_non_numeric(client: FlaskClient) -> None:
    rv = client.get("/test?filter=blur&filter_strength=abc")
    assert rv.status_code == 400


def test_filter_strength_non_positive(client: FlaskClient) -> None:
    rv = client.get("/test?filter=blur&filter_strength=0")
    assert rv.status_code == 400


def test_filter_strength_inf(client: FlaskClient) -> None:
    rv = client.get("/test?filter=blur&filter_strength=inf")
    assert rv.status_code == 400


def test_filter_strength_nan(client: FlaskClient) -> None:
    rv = client.get("/test?filter=blur&filter_strength=nan")
    assert rv.status_code == 400


def test_filter_strength_without_filter(client: FlaskClient) -> None:
    rv = client.get("/test?filter_strength=5")
    assert rv.status_code == 400


def test_filter_strength_with_non_strength_filter(client: FlaskClient) -> None:
    rv = client.get("/test?filter=contour&filter_strength=5")
    assert rv.status_code == 400


def test_filter_strength_negative(client: FlaskClient) -> None:
    rv = client.get("/test?filter=blur&filter_strength=-1")
    assert rv.status_code == 400


def test_filter_sepia_strength_above_one(client: FlaskClient) -> None:
    rv = client.get("/test?filter=sepia&filter_strength=5")
    assert rv.status_code == 200


def test_filter_strength_exceeds_max(client: FlaskClient) -> None:
    rv = client.get("/test?filter=blur&filter_strength=999999")
    assert rv.status_code == 400


def test_filter_strength_at_max(client: FlaskClient) -> None:
    rv = client.get("/test?filter=blur&filter_strength=10000")
    assert rv.status_code == 200


def test_filter_grayscale_preserves_dimensions(client: FlaskClient) -> None:
    rv = client.get("/test?filter=grayscale&width=100&height=50")
    assert rv.status_code == 200
    img = Image.open(BytesIO(rv.data))
    assert img.size == (100, 50)


def test_filter_grayscale_with_rgba(client: FlaskClient) -> None:
    rv = client.get("/test?filter=grayscale&mode=RGBA&color=transparent")
    assert rv.status_code == 200
    img = Image.open(BytesIO(rv.data))
    assert img.mode == "RGBA"


# QR code tests


def test_qr_code_basic(client: FlaskClient) -> None:
    rv = client.get("/test?qr=https://example.com&height=400")
    assert rv.status_code == 200
    assert rv.headers["Content-Type"] == "image/png"
    img = Image.open(BytesIO(rv.data))
    assert img.size == (600, 400)


def test_qr_code_with_custom_size(client: FlaskClient) -> None:
    rv = client.get("/test?qr=https://example.com&width=400&height=400")
    assert rv.status_code == 200
    img = Image.open(BytesIO(rv.data))
    assert img.size == (400, 400)


def test_qr_code_position(client: FlaskClient) -> None:
    rv = client.get("/test?qr=https://example.com&height=400&qr_position=top-left")
    assert rv.status_code == 200


def test_qr_code_position_bottom_right(client: FlaskClient) -> None:
    rv = client.get("/test?qr=https://example.com&height=400&qr_position=bottom-right")
    assert rv.status_code == 200


def test_qr_code_xy(client: FlaskClient) -> None:
    rv = client.get("/test?qr=https://example.com&height=400&qr_x=10&qr_y=10")
    assert rv.status_code == 200


def test_qr_code_offset(client: FlaskClient) -> None:
    rv = client.get("/test?qr=https://example.com&height=400&qr_offset_x=5&qr_offset_y=5")
    assert rv.status_code == 200


def test_qr_code_custom_box_size(client: FlaskClient) -> None:
    rv = client.get("/test?qr=https://example.com&qr_size=20&width=700&height=700")
    assert rv.status_code == 200


def test_qr_code_error_correction(client: FlaskClient) -> None:
    for level in ("L", "M", "Q", "H"):
        rv = client.get(f"/test?qr=https://example.com&height=400&qr_error_correction={level}")
        assert rv.status_code == 200


def test_qr_code_invalid_error_correction(client: FlaskClient) -> None:
    rv = client.get("/test?qr=https://example.com&qr_error_correction=X")
    assert rv.status_code == 400


def test_qr_code_invalid_size(client: FlaskClient) -> None:
    rv = client.get("/test?qr=https://example.com&qr_size=0")
    assert rv.status_code == 400


def test_qr_code_invalid_size_negative(client: FlaskClient) -> None:
    rv = client.get("/test?qr=https://example.com&qr_size=-1")
    assert rv.status_code == 400


def test_qr_code_non_numeric_qr_size(client: FlaskClient) -> None:
    rv = client.get("/test?qr=https://example.com&qr_size=abc")
    assert rv.status_code == 400


def test_qr_code_invalid_position(client: FlaskClient) -> None:
    rv = client.get("/test?qr=https://example.com&qr_position=invalid")
    assert rv.status_code == 400


def test_qr_code_with_rgba(client: FlaskClient) -> None:
    rv = client.get("/test?qr=https://example.com&height=400&mode=RGBA&color=transparent")
    assert rv.status_code == 200


def test_qr_code_image_has_qr_content(client: FlaskClient) -> None:
    rv = client.get("/test?qr=https://example.com&height=400")
    assert rv.status_code == 200
    img = Image.open(BytesIO(rv.data))
    assert img.mode in ("RGB", "RGBA")


def test_qr_code_non_numeric_qr_x(client: FlaskClient) -> None:
    rv = client.get("/test?qr=https://example.com&qr_x=abc")
    assert rv.status_code == 400


def test_qr_code_non_numeric_qr_y(client: FlaskClient) -> None:
    rv = client.get("/test?qr=https://example.com&qr_y=abc")
    assert rv.status_code == 400


def test_qr_code_non_numeric_qr_offset_x(client: FlaskClient) -> None:
    rv = client.get("/test?qr=https://example.com&qr_offset_x=abc")
    assert rv.status_code == 400


def test_qr_code_non_numeric_qr_offset_y(client: FlaskClient) -> None:
    rv = client.get("/test?qr=https://example.com&qr_offset_y=abc")
    assert rv.status_code == 400


# Multi-text layer tests


def test_two_text_layers(client: FlaskClient) -> None:
    rv = client.get("/First?text2=Second")
    assert rv.status_code == 200
    assert rv.headers["Content-Type"] == "image/png"


def test_three_text_layers(client: FlaskClient) -> None:
    rv = client.get("/First?text2=Second&text3=Third")
    assert rv.status_code == 200
    assert rv.headers["Content-Type"] == "image/png"


def test_text_layer_with_position(client: FlaskClient) -> None:
    rv = client.get("/First?text2=Second&position2=bottom-right")
    assert rv.status_code == 200


def test_text_layer_with_fill(client: FlaskClient) -> None:
    rv = client.get("/First?text2=Second&fill2=red")
    assert rv.status_code == 200


def test_text_layer_with_font_size(client: FlaskClient) -> None:
    rv = client.get("/First?text2=Second&font_size2=60")
    assert rv.status_code == 200


def test_text_layer_with_xy(client: FlaskClient) -> None:
    rv = client.get("/First?text2=Second&x2=100&y2=50")
    assert rv.status_code == 200


def test_text_layer_with_rotation(client: FlaskClient) -> None:
    rv = client.get("/First?text2=Second&rotation2=45")
    assert rv.status_code == 200


def test_text_layer_with_shadow(client: FlaskClient) -> None:
    rv = client.get("/First?text2=Second&shadow_color2=gray")
    assert rv.status_code == 200


def test_text_layer_with_stroke(client: FlaskClient) -> None:
    rv = client.get("/First?text2=Second&stroke_width2=3&stroke_color2=red")
    assert rv.status_code == 200


def test_text_layer_with_gradient(client: FlaskClient) -> None:
    rv = client.get("/First?text2=Second&gradient_from2=red&gradient_to2=blue")
    assert rv.status_code == 200


def test_text_layer_non_numeric_font_size(client: FlaskClient) -> None:
    rv = client.get("/First?text2=Second&font_size2=abc")
    assert rv.status_code == 400


def test_text_layer_non_numeric_rotation(client: FlaskClient) -> None:
    rv = client.get("/First?text2=Second&rotation2=abc")
    assert rv.status_code == 400


def test_text_layer_all_effects(client: FlaskClient) -> None:
    rv = client.get(
        "/First?text2=Second&fill2=red&font_size2=60&position2=bottom-right&rotation2=15&shadow_color2=gray"
    )
    assert rv.status_code == 200
