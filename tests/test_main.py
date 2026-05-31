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


def test_validate_url_public_ip_allowed():
    validate_background_image_url("http://8.8.8.8/image.jpg")


def test_validate_url_public_domain_allowed():
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


def test_transparent_background(client):
    rv = client.get("/test?mode=RGBA&color=transparent")
    assert rv.status_code == 200
    assert rv.headers["Content-Type"] == "image/png"


def test_backgroundimage_success(client):
    img = Image.new("RGB", (100, 100), (255, 0, 0))
    buf = BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)

    mock_response = MagicMock()
    mock_response.raw = buf
    mock_response.raise_for_status.return_value = None

    with patch("pillow_web.image.requests.get", return_value=mock_response):
        rv = client.get("/test?backgroundimage=http://example.com/img.png")
        assert rv.status_code == 200
        assert rv.headers["Content-Type"] == "image/png"


def test_backgroundimage_fetch_failure(client):
    with patch(
        "pillow_web.image.requests.get", side_effect=requests.exceptions.ConnectionError("Connection error")
    ):
        rv = client.get("/test?backgroundimage=http://example.com/img.png")
        assert rv.status_code == 400
        assert "背景画像の読み込みに失敗" in rv.data.decode()


def test_invalid_width_non_numeric(client):
    rv = client.get("/test?width=abc")
    assert rv.status_code == 400


def test_invalid_height_non_numeric(client):
    rv = client.get("/test?height=abc")
    assert rv.status_code == 400


def test_invalid_spacing_non_numeric(client):
    rv = client.get("/test?spacing=abc")
    assert rv.status_code == 400


def test_invalid_font_size_non_numeric(client):
    rv = client.get("/test?font_size=abc")
    assert rv.status_code == 400


def test_width_exceeds_max_with_message(client):
    rv = client.get(f"/test?width={MAX_IMAGE_SIZE + 1}")
    assert rv.status_code == 400
    assert "must not exceed" in rv.data.decode()


def test_height_exceeds_max_with_message(client):
    rv = client.get(f"/test?height={MAX_IMAGE_SIZE + 1}")
    assert rv.status_code == 400
    assert "must not exceed" in rv.data.decode()


# Text position tests


def test_position_top_left(client):
    rv = client.get("/test?position=top-left")
    assert rv.status_code == 200


def test_position_top_center(client):
    rv = client.get("/test?position=top-center")
    assert rv.status_code == 200


def test_position_top_right(client):
    rv = client.get("/test?position=top-right")
    assert rv.status_code == 200


def test_position_center_left(client):
    rv = client.get("/test?position=center-left")
    assert rv.status_code == 200


def test_position_center(client):
    rv = client.get("/test?position=center")
    assert rv.status_code == 200


def test_position_center_right(client):
    rv = client.get("/test?position=center-right")
    assert rv.status_code == 200


def test_position_bottom_left(client):
    rv = client.get("/test?position=bottom-left")
    assert rv.status_code == 200


def test_position_bottom_center(client):
    rv = client.get("/test?position=bottom-center")
    assert rv.status_code == 200


def test_position_bottom_right(client):
    rv = client.get("/test?position=bottom-right")
    assert rv.status_code == 200


def test_position_underscore_variant(client):
    rv = client.get("/test?position=bottom_right")
    assert rv.status_code == 200


def test_position_invalid(client):
    rv = client.get("/test?position=invalid-position")
    assert rv.status_code == 400


def test_xy_coordinates(client):
    rv = client.get("/test?x=100&y=50")
    assert rv.status_code == 200


def test_x_only(client):
    rv = client.get("/test?x=100")
    assert rv.status_code == 200


def test_y_only(client):
    rv = client.get("/test?y=50")
    assert rv.status_code == 200


def test_xy_non_numeric(client):
    rv = client.get("/test?x=abc")
    assert rv.status_code == 400


def test_offset_xy(client):
    rv = client.get("/test?offset_x=10&offset_y=20")
    assert rv.status_code == 200


def test_position_with_offset(client):
    rv = client.get("/test?position=bottom-right&offset_x=-10&offset_y=-10")
    assert rv.status_code == 200


def test_xy_with_offset(client):
    rv = client.get("/test?x=200&y=100&offset_x=5&offset_y=5")
    assert rv.status_code == 200


def test_offset_x_non_numeric(client):
    rv = client.get("/test?offset_x=abc")
    assert rv.status_code == 400


def test_offset_y_non_numeric(client):
    rv = client.get("/test?offset_y=abc")
    assert rv.status_code == 400
