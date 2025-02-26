#!/bin/bash
set -e

# Report the optimization level
echo "Running with PYTHONOPTIMIZE=${PYTHONOPTIMIZE:-0}"

# Then run the main command
if [ "$BUILD_ENV" = "dev" ]; then
  pytest -v --log-cli-level=INFO tests/
  cp /tmp/memory_profile_O*.json /app/memory_profiles/ 2>/dev/null || true
else
  exec mcp-server
fi
