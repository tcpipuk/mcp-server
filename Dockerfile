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

# Add the rest of the project source code and install it
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --frozen ${BUILD_ENV:+"--dev"} --no-editable

# Prepare runtime image
FROM python:3.13-slim-bookworm AS runtime
WORKDIR /app
ARG BUILD_ENV=prod

# Install system dependencies and create user in one layer
RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential \
  && rm -rf /var/lib/apt/lists/* \
  && groupadd -r app \
  && useradd -r -g app app \
  && python -m venv /app/sandbox-venv \
  && /app/sandbox-venv/bin/pip install --no-cache-dir \
  aiodns \
  aiohttp \
  beautifulsoup4 \
  ruff \
  numpy \
  pandas \
  requests \
  && rm -rf /root/.cache

# Copy only necessary files from build stage
COPY --from=uv --chown=app:app /app/mcp_server ./mcp_server/
COPY --from=uv --chown=app:app /app/.venv ./.venv/
COPY --from=uv --chown=app:app /app/pyproject.toml ./
COPY --from=uv --chown=app:app /app/pytest.ini ./
COPY --from=uv --chown=app:app /app/tests ./tests/

# Switch to non-root user and set up environment
USER app
ENV PATH="/app/.venv/bin:/app/sandbox-venv/bin:$PATH" \
  OPENBLAS_NUM_THREADS=1 \
  RUFF_CACHE_DIR=/tmp/.ruff_cache \
  SANDBOX_PYTHON="/app/sandbox-venv/bin/python" \
  SANDBOX_RUFF="/app/sandbox-venv/bin/ruff"

# Use conditional entrypoint
ENTRYPOINT ["/bin/sh", "-c", "if [ \"$BUILD_ENV\" = \"dev\" ]; then pytest tests/; else exec mcp-server; fi"]
