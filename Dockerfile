FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY src/ ./src/

RUN uv sync --locked --no-dev --frozen

EXPOSE 5000

CMD ["uv", "run", "main.py"]
