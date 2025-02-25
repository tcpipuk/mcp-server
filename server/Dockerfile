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

# Add the source code and install main project dependencies
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --frozen ${BUILD_ENV:+"--dev"} --no-editable

# Prepare runtime image
FROM python:3.13-slim-bookworm AS runtime
WORKDIR /app
ARG BUILD_ENV=prod

# Install minimal system dependencies, create user, and ensure /workspace is writable
RUN apt-get update \
  && apt-get install -y --no-install-recommends socat \
  && rm -rf /var/lib/apt/lists/* \
  && groupadd -r appuser \
  && useradd -r -g appuser appuser

# Copy only necessary files from build stage
COPY --from=uv --chown=appuser:appuser /app/ .

# Switch to non-root user and set up environment
USER appuser
ENV PATH="/app/.venv/bin:$PATH"

# Use wrapper script to handle startup
ENTRYPOINT ["/app/entrypoint.sh"]
