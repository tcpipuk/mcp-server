FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim
WORKDIR /opt

# Configure shell to exit on any error, including pipe failures
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install system dependencies and configure user
RUN apt-get update && apt-get install -y --no-install-recommends \
  git \
  screen \
  socat \
  tree \
  && rm -rf /var/lib/apt/lists/* \
  # Create sandbox user and group
  && groupadd -g 1000 sandbox \
  && useradd -r -u 1000 -g sandbox sandbox \
  --home /workspace --shell /bin/bash \
  && mkdir -p -m 750 /workspace \
  && chown sandbox:sandbox /workspace

# Configure uv behaviour and install dependencies
ENV UV_COMPILE_BYTECODE=1 \
  UV_LINK_MODE=copy \
  UV_NO_CACHE=1 \
  UV_PROJECT_ENVIRONMENT=venv

COPY --chown=sandbox:sandbox pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --frozen ${BUILD_ENV:+"--dev"} --no-editable

# Copy entrypoint script
COPY --chmod=755 --chown=0:0 entrypoint.sh /

# Switch to non-root user for security
USER sandbox

# Configure Python environment
ENV LANG=C.UTF-8 \
  OPENBLAS_NUM_THREADS=1 \
  PATH="/opt/venv/bin:$PATH" \
  PYTHONPATH="/opt/venv" \
  PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1

# Expose port for TCP connections
EXPOSE 8080

# Set working directory and entrypoint
WORKDIR /workspace
ENTRYPOINT ["/entrypoint.sh"]
