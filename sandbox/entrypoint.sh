#!/bin/bash
exec socat UNIX-LISTEN:"${SANDBOX_SOCKET}",fork,mode=600 EXEC:"/bin/bash"
