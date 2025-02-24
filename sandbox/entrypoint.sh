#!/bin/bash
set -e

# shellcheck disable=SC1091
source /opt/venv/bin/activate

echo "Starting sandbox service..."
echo "Listening for connections on 0.0.0.0:8080"

# Start socat as sandbox user
exec socat \
  TCP-LISTEN:8080,fork,reuseaddr,bind=0.0.0.0 \
  EXEC:"/bin/bash"

echo "Stopping sandbox service..."
