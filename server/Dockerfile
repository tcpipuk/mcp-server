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

# Set default build environment
ARG BUILD_ENV=prod

# Install minimal system dependencies and create runtime user
RUN apt-get update \
  && apt-get install -y --no-install-recommends socat \
  && rm -rf /var/lib/apt/lists/* \
  && groupadd -g 1000 appuser \
  && useradd -u 1000 -g 1000 -m appuser

# Copy only necessary files from build stage
COPY --from=uv --chown=appuser:appuser /app/ .

# Switch to non-root user

# Set environment variables for runtime
USER appuser
ENV PATH="/app/.venv/bin:$PATH" \
  PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1

# Use wrapper script to handle startup
ENTRYPOINT ["/app/entrypoint.sh"]
