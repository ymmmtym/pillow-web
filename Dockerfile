FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md main.py ./
COPY src/ ./src/

RUN pip install --no-cache-dir .

EXPOSE 5000

CMD ["python", "main.py"]
