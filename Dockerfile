# Build stage using uv with a frozen lockfile and dependency caching
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS uv
WORKDIR /app

# Enable bytecode compilation and copy mode
ENV UV_COMPILE_BYTECODE=1 \
  UV_LINK_MODE=copy

# Install dependencies using the lockfile and settings
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --frozen --no-install-project ${BUILD_ENV:+"--dev"} --no-editable

# Add the source code and install dependencies
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --frozen ${BUILD_ENV:+"--dev"} --no-editable

# Prepare runtime image
FROM python:3.13-slim-bookworm AS runtime
WORKDIR /app
ARG BUILD_ENV=prod

# Install system dependencies, missing commands, create user, and ensure /workspace is writable
RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential \
  git \
  openssh-client \
  tree \
  && rm -rf /var/lib/apt/lists/* \
  && python -m venv /app/sandbox-venv \
  && /app/sandbox-venv/bin/pip install --no-cache-dir \
  aiodns \
  aiohttp \
  beautifulsoup4 \
  ruff \
  numpy \
  pandas \
  requests \
  && rm -rf /root/.cache \
  && groupadd -r app \
  && useradd -r -g app app \
  && mkdir -p /workspace \
  && chown app:app /workspace \
  && mkdir -p -m 700 ~/.ssh \
  && chown app:app ~/.ssh

# Copy only necessary files from build stage
COPY --from=uv --chown=app:app /app/ .

# Switch to non-root user and set up environment
USER app
ENV PATH="/app/.venv/bin:/app/sandbox-venv/bin:$PATH" \
  OPENBLAS_NUM_THREADS=1 \
  RUFF_CACHE_DIR=/tmp/.ruff_cache \
  SANDBOX_PYTHON="/app/sandbox-venv/bin/python" \
  SANDBOX_RUFF="/app/sandbox-venv/bin/ruff"

# Use wrapper script to handle startup
ENTRYPOINT ["/app/docker-entrypoint.sh"]
