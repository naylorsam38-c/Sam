# Build context must be the repo root (see docker-compose.yml) because this
# service depends on the shared libs/core and gpu packages.
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY libs/core ./libs/core
COPY gpu ./gpu
COPY config ./config
COPY database ./database
COPY alembic.ini ./alembic.ini
COPY apps/control/src ./apps/control/src

ENV PYTHONPATH=/app/libs/core:/app:/app/apps/control/src

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn control.main:app --host 0.0.0.0 --port 8000"]
