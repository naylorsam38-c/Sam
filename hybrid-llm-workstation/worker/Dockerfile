# Build context must be the repo root (see docker-compose.yml).
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY libs/core ./libs/core
COPY gpu ./gpu
COPY config ./config
COPY worker/src ./worker/src

ENV PYTHONPATH=/app/libs/core:/app:/app/worker/src

CMD ["python", "-m", "worker.main"]
