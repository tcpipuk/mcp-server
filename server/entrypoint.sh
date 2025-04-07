#!/bin/bash
set -e

# Then run the main command
if [ "$BUILD_ENV" = "dev" ]; then
    pytest -v --log-cli-level=INFO tests/
else
    exec mcp-server
fi
