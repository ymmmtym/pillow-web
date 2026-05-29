import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from main import app, _validate_background_image_url, _is_private_ip

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
