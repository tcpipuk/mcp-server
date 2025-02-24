#!/bin/bash
set -e

# shellcheck disable=SC1091
source /opt/venv/bin/activate

# Start socat as sandbox user
exec socat \
  UNIX-LISTEN:"${SANDBOX_SOCKET}",fork,mode=600,user=sandbox,group=sandbox \
  EXEC:"/bin/bash"
