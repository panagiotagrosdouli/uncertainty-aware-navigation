FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml requirements.txt ./
RUN python -m pip install --upgrade pip && \
    python -m pip install -e '.[dev]'

COPY . .

CMD ["pytest", "-q"]
