from __future__ import annotations

import sys
from typing import Generator

import pytest
from flask.testing import FlaskClient

sys.path.insert(0, '/workspace')
from main import app

@pytest.fixture
def client() -> Generator[FlaskClient, None, None]:
    app.testing = True
    with app.test_client() as client:
        yield client

def test_images_png_default(client: FlaskClient) -> None:
    rv = client.get('/test')
    assert rv.status_code == 200
    assert rv.headers['Content-Type'] == 'image/png'

def test_images_png_explicit(client: FlaskClient) -> None:
    rv = client.get('/test?format=png')
    assert rv.status_code == 200
    assert rv.headers['Content-Type'] == 'image/png'

def test_images_jpg(client: FlaskClient) -> None:
    rv = client.get('/test?format=jpg')
    assert rv.status_code == 200
    assert rv.headers['Content-Type'] == 'image/jpeg'

def test_images_jpeg(client: FlaskClient) -> None:
    rv = client.get('/test?format=jpeg')
    assert rv.status_code == 200
    assert rv.headers['Content-Type'] == 'image/jpeg'

def test_invalid_format(client: FlaskClient) -> None:
    rv = client.get('/test?format=gif')
    assert rv.status_code == 400
