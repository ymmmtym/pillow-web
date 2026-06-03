import pytest

from main import app, limiter


@pytest.fixture(autouse=True)
def _disable_rate_limiter() -> None:
    limiter.enabled = False
    app.config["RATELIMIT_ENABLED"] = False
