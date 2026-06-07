FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.19 /uv /bin/uv

WORKDIR /app

COPY pyproject.toml README.md main.py uv.lock ./
COPY src/ ./src/

RUN uv sync --no-dev --frozen

EXPOSE 5000

CMD ["uv", "run", "main.py"]
