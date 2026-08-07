FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first for better layer caching.
COPY pyproject.toml README.md ./
COPY citely ./citely
RUN pip install --upgrade pip && pip install .

# Alembic config lives at the repo root and is not part of the wheel, but the image must
# be able to run `alembic upgrade head` (the compose `migrate` service does exactly that).
# The migration scripts themselves come along inside ./citely.
COPY alembic.ini ./

EXPOSE 8000

CMD ["uvicorn", "citely.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
