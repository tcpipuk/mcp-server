#!/bin/bash
set -e

# Run secure startup first
python -c "from mcp_server.startup import secure_startup; secure_startup()"

# Then run the main command
if [ "$BUILD_ENV" = "dev" ]; then
  pytest -v --log-cli-level=INFO tests/
else
  exec mcp-server
fi
