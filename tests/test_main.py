
import pytest
import sys
from io import BytesIO
from unittest.mock import patch, MagicMock
from PIL import Image
sys.path.insert(0, '/workspace')
from main import app

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

def test_transparent_background(client):
    rv = client.get('/test?mode=RGBA&color=transparent')
    assert rv.status_code == 200
    assert rv.headers['Content-Type'] == 'image/png'

def test_backgroundimage(client):
    img = Image.new('RGB', (100, 100), 'blue')
    buf = BytesIO()
    img.save(buf, 'PNG')
    buf.seek(0)

    mock_response = MagicMock()
    mock_response.raw = buf

    with patch('main.requests.get', return_value=mock_response):
        rv = client.get('/test?backgroundimage=http://example.com/img.png')
    assert rv.status_code == 200
    assert rv.headers['Content-Type'] == 'image/png'

def test_invalid_width(client):
    rv = client.get('/test?width=abc')
    assert rv.status_code == 400

def test_invalid_height(client):
    rv = client.get('/test?height=abc')
    assert rv.status_code == 400

def test_invalid_font_size(client):
    rv = client.get('/test?font_size=abc')
    assert rv.status_code == 400

def test_size_limit_exceeded(client):
    rv = client.get('/test?width=2001')
    assert rv.status_code == 400
