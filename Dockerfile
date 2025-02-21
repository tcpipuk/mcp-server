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

# Install necessary system packages for namespace isolation
RUN apt-get update && apt-get install -y cgroup-tools && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r app && useradd -r -g app app

# Set up cgroups for sandbox limits
RUN mkdir -p /sys/fs/cgroup/python-sandbox && \
  chown -R app:app /sys/fs/cgroup/python-sandbox

# Create a separate sandbox environment and install Ruff for linting
RUN python -m venv /app/sandbox-venv && \
  /app/sandbox-venv/bin/pip install ruff

WORKDIR /app

# Copy project files from the build stage.
COPY --from=uv --chown=app:app /app/mcp_server /app/mcp_server
COPY --from=uv --chown=app:app /app/pyproject.toml /app/
COPY --from=uv --chown=app:app /app/.venv /app/.venv

# Set up cgroup limits for memory and CPU
RUN echo "500M" > /sys/fs/cgroup/python-sandbox/memory.max && \
  echo "100000 100000" > /sys/fs/cgroup/python-sandbox/cpu.max

# Switch to non-root user
USER app

# Place executables in the environment at the front of the PATH
ENV PATH="/app/.venv/bin:/app/sandbox-venv/bin:$PATH"

# Configure sandbox environment variables for tool use
ENV SANDBOX_PYTHON="/app/sandbox-venv/bin/python"
ENV SANDBOX_RUFF="/app/sandbox-venv/bin/ruff"

# Set the entrypoint command
ENTRYPOINT ["mcp-server"]
