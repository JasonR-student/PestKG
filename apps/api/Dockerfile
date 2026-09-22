FROM python:3.12-slim-bookworm AS wheels

ARG PIP_INDEX_URL=https://pypi.org/simple

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY apps/api/requirements.txt ./requirements.txt
RUN pip wheel --wheel-dir /wheels --index-url "$PIP_INDEX_URL" -r requirements.txt
COPY apps/api/pyproject.toml ./pyproject.toml
COPY apps/api/src ./src
RUN pip wheel --wheel-dir /wheels --no-deps .

FROM python:3.12-slim-bookworm AS runtime

ARG BUILD_DATE=unknown
ARG VCS_REF=unknown
ARG VERSION=dev

LABEL org.opencontainers.image.title="PestKG API" \
      org.opencontainers.image.description="Read-only, release-aware pesticide knowledge graph API" \
      org.opencontainers.image.version="$VERSION" \
      org.opencontainers.image.created="$BUILD_DATE" \
      org.opencontainers.image.revision="$VCS_REF" \
      org.opencontainers.image.licenses="MIT"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app
COPY --from=wheels /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels pestkg-api \
    && rm -rf /wheels

USER app
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=3)"]

CMD ["uvicorn", "pestkg_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
