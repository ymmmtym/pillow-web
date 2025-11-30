
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
