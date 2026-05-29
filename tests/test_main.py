
import pytest
import sys
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
