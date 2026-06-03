FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first for better layer caching.
COPY pyproject.toml README.md ./
COPY citely ./citely
RUN pip install --upgrade pip && pip install .

EXPOSE 8000

CMD ["uvicorn", "citely.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
