FROM python:3.11-slim AS builder

WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.11-slim

RUN useradd --create-home --shell /usr/sbin/nologin app
COPY --from=builder /install /usr/local
USER app

EXPOSE 8000
CMD ["uvicorn", "stream_catalog.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
