# Build stage using uv with a frozen lockfile and dependency caching
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS uv
WORKDIR /app

# Enable bytecode compilation and copy mode
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Install dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
  --mount=type=bind,source=uv.lock,target=uv.lock \
  --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
  uv sync --frozen --no-install-project --no-dev --no-editable

# Add the rest of the project source code and install it
ADD . /app
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --frozen --no-dev --no-editable

# Prepare runtime image
FROM python:3.13-slim-bookworm
WORKDIR /app

# Install build dependencies for numpy/pandas
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r app && useradd -r -g app app

# Create and populate sandbox environment
RUN python -m venv /app/sandbox-venv && \
    /app/sandbox-venv/bin/pip install --no-cache-dir \
        aiodns \
        aiohttp \
        beautifulsoup4 \
        ruff \
        numpy \
        pandas \
        requests \
    && rm -rf /root/.cache

# Copy project files from the build stage
COPY --from=uv --chown=app:app /app/mcp_server /app/mcp_server
COPY --from=uv --chown=app:app /app/pyproject.toml /app/
COPY --from=uv --chown=app:app /app/.venv /app/.venv

# Switch to non-root user
USER app

# Place executables in the environment
ENV PATH="/app/.venv/bin:/app/sandbox-venv/bin:$PATH"

# Configure environment variables
ENV OPENBLAS_NUM_THREADS=8
ENV RUFF_CACHE_DIR=/tmp/.ruff_cache
ENV SANDBOX_PYTHON="/app/sandbox-venv/bin/python"
ENV SANDBOX_RUFF="/app/sandbox-venv/bin/ruff"

ENTRYPOINT ["mcp-server"]
