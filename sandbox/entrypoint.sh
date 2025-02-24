#!/bin/bash
set -e

# Shell wrapper to execute for each connection
cat >/tmp/shell_wrapper.sh <<'EOF'
#!/bin/bash
source /opt/venv/bin/activate
PS1="(sandbox) \u@\h:\w\$ "
exec bash --login
EOF

chmod +x /tmp/shell_wrapper.sh

echo "Starting sandbox service..."
echo "Listening for connections on 0.0.0.0:8080"

# Start socat as sandbox user with pseudo-terminal
exec socat \
  TCP-LISTEN:8080,fork,reuseaddr,bind=0.0.0.0 \
  EXEC:"/tmp/shell_wrapper.sh",pty,stderr,setsid,sigint,sane,raw,echo=0

echo "Stopping sandbox service..."
