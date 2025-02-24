################################
# Build stage - Dependencies
################################
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS uv
WORKDIR /opt

# Configure uv behaviour
ENV UV_COMPILE_BYTECODE=1 \
  UV_LINK_MODE=copy

# Install Python dependencies
# Uses build cache for faster subsequent builds
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --frozen ${BUILD_ENV:+"--dev"} --no-editable

################################
# Runtime stage
################################
FROM debian:bookworm-slim

# Configure shell to exit on any error, including pipe failures
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Copy runtime scripts
COPY --chmod=755 entrypoint.sh /

# Install system dependencies and configure user
# Note: Packages are sorted alphabetically for maintainability
RUN apt-get update && apt-get install -y --no-install-recommends \
  git \
  screen \
  socat \
  && rm -rf /var/lib/apt/lists/* \
  # Create sandbox user and group
  && groupadd -g 1000 sandbox \
  && useradd -r -u 1000 -g sandbox sandbox \
  --home /workspace --shell /bin/bash \
  && mkdir -p -m 750 /workspace \
  && chown sandbox:sandbox /workspace

# Copy Python virtual environment from build stage
COPY --from=uv --chown=sandbox:sandbox /opt/.venv /opt/venv

# Switch to non-root user for security
USER sandbox

# Configure Python environment
ENV LANG=C.UTF-8 \
  OPENBLAS_NUM_THREADS=1 \
  PATH="/opt/venv/bin:$PATH" \
  PYTHONPATH="/opt/venv" \
  PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1

# Set working directory and entrypoint
WORKDIR /workspace
ENTRYPOINT ["/entrypoint.sh"]
