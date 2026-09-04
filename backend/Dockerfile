# syntax=docker/dockerfile:1
FROM python:3.12-slim AS runtime

ARG UV_VERSION=0.7.12

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    LEARNING_RUNTIME_DIR=/runtime

RUN groupadd --gid 10001 learning \
    && useradd --uid 10001 --gid learning --no-create-home --shell /usr/sbin/nologin learning \
    && mkdir -p /app /runtime/uploads \
    && chown -R learning:learning /app /runtime \
    && pip install --no-cache-dir "uv==${UV_VERSION}"

WORKDIR /app
COPY --chown=learning:learning pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY --chown=learning:learning app ./app

USER learning
EXPOSE 8000
VOLUME ["/runtime"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD [".venv/bin/python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=3).read()"]

CMD [".venv/bin/python", "-m", "app.serve"]
