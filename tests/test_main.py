from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch
import sys

import pytest
import requests
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from main import app, _validate_background_image_url, _is_private_ip, MAX_IMAGE_SIZE

@pytest.fixture
def client():
    app.testing = True
    with app.test_client() as client:
        yield client

def test_images_png_default(client):
    rv = client.get('/test')
    assert rv.status_code == 200
    assert rv.headers['Content-Type'] == 'image/png'

def test_images_png_explicit(client):
    rv = client.get('/test?format=png')
    assert rv.status_code == 200
    assert rv.headers['Content-Type'] == 'image/png'

def test_images_jpg(client):
    rv = client.get('/test?format=jpg')
    assert rv.status_code == 200
    assert rv.headers['Content-Type'] == 'image/jpeg'

def test_images_jpeg(client):
    rv = client.get('/test?format=jpeg')
    assert rv.status_code == 200
    assert rv.headers['Content-Type'] == 'image/jpeg'

def test_invalid_format(client):
    rv = client.get('/test?format=gif')
    assert rv.status_code == 400



# SSRF validation tests

def test_validate_url_private_ipv4_loopback():
    with pytest.raises(ValueError, match="プライベートネットワーク"):
        _validate_background_image_url("http://127.0.0.1:5000/image.jpg")


def test_validate_url_private_ipv4_10():
    with pytest.raises(ValueError, match="プライベートネットワーク"):
        _validate_background_image_url("http://10.0.0.1/image.jpg")


def test_validate_url_private_ipv4_172():
    with pytest.raises(ValueError, match="プライベートネットワーク"):
        _validate_background_image_url("http://172.16.0.1/image.jpg")


def test_validate_url_private_ipv4_192():
    with pytest.raises(ValueError, match="プライベートネットワーク"):
        _validate_background_image_url("http://192.168.1.1/image.jpg")


def test_validate_url_private_ipv6_loopback():
    with pytest.raises(ValueError, match="プライベートネットワーク"):
        _validate_background_image_url("http://[::1]:5000/image.jpg")


def test_validate_url_invalid_scheme_file():
    with pytest.raises(ValueError, match="httpもしくはhttps"):
        _validate_background_image_url("file:///etc/passwd")


def test_validate_url_invalid_scheme_ftp():
    with pytest.raises(ValueError, match="httpもしくはhttps"):
        _validate_background_image_url("ftp://example.com/image.jpg")


def test_validate_url_no_hostname():
    with pytest.raises(ValueError, match="ホスト名"):
        _validate_background_image_url("http:///image.jpg")


def test_validate_url_public_ip_allowed():
    _validate_background_image_url("http://8.8.8.8/image.jpg")


def test_validate_url_public_domain_allowed():
    _validate_background_image_url("https://example.com/image.jpg")


def test_backgroundimage_private_ip_blocked(client):
    rv = client.get('/test?backgroundimage=http://127.0.0.1:5000/image.jpg')
    assert rv.status_code == 400
    assert "プライベートネットワーク" in rv.data.decode()


def test_backgroundimage_invalid_scheme_blocked(client):
    rv = client.get('/test?backgroundimage=file:///etc/passwd')
    assert rv.status_code == 400
    assert "httpもしくはhttps" in rv.data.decode()

def test_width_zero(client):
    rv = client.get('/test?width=0')
    assert rv.status_code == 400

def test_width_negative(client):
    rv = client.get('/test?width=-1')
    assert rv.status_code == 400

def test_width_too_large(client):
    rv = client.get('/test?width=99999')
    assert rv.status_code == 400

def test_height_zero(client):
    rv = client.get('/test?height=0')
    assert rv.status_code == 400

def test_height_negative(client):
    rv = client.get('/test?height=-1')
    assert rv.status_code == 400

def test_height_too_large(client):
    rv = client.get('/test?height=99999')
    assert rv.status_code == 400

def test_max_size_boundary(client):
    rv = client.get('/test?width=4096&height=4096')
    assert rv.status_code == 200


def test_transparent_background(client):
    rv = client.get('/test?mode=RGBA&color=transparent')
    assert rv.status_code == 200
    assert rv.headers['Content-Type'] == 'image/png'


def test_backgroundimage_success(client):
    img = Image.new('RGB', (100, 100), (255, 0, 0))
    buf = BytesIO()
    img.save(buf, 'PNG')
    buf.seek(0)

    mock_response = MagicMock()
    mock_response.raw = buf
    mock_response.raise_for_status.return_value = None

    with patch('main.requests.get', return_value=mock_response):
        rv = client.get('/test?backgroundimage=http://example.com/img.png')
        assert rv.status_code == 200
        assert rv.headers['Content-Type'] == 'image/png'


def test_backgroundimage_fetch_failure(client):
    with patch('main.requests.get', side_effect=requests.exceptions.ConnectionError("Connection error")):
        rv = client.get('/test?backgroundimage=http://example.com/img.png')
        assert rv.status_code == 400
        assert "背景画像の読み込みに失敗" in rv.data.decode()


def test_invalid_width_non_numeric(client):
    rv = client.get('/test?width=abc')
    assert rv.status_code == 400


def test_invalid_height_non_numeric(client):
    rv = client.get('/test?height=abc')
    assert rv.status_code == 400


def test_invalid_spacing_non_numeric(client):
    rv = client.get('/test?spacing=abc')
    assert rv.status_code == 400


def test_invalid_font_size_non_numeric(client):
    rv = client.get('/test?font_size=abc')
    assert rv.status_code == 400


def test_width_exceeds_max_with_message(client):
    rv = client.get(f'/test?width={MAX_IMAGE_SIZE + 1}')
    assert rv.status_code == 400
    assert "must not exceed" in rv.data.decode()


def test_height_exceeds_max_with_message(client):
    rv = client.get(f'/test?height={MAX_IMAGE_SIZE + 1}')
    assert rv.status_code == 400
    assert "must not exceed" in rv.data.decode()
