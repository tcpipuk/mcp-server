# MCP Server

Give your AI assistants the power to help you more effectively. This server lets them safely access
websites and search the web - with clear feedback about what's happening and helpful error messages
when things go wrong.

- [🛠️ What tools does this server offer?](#️-what-tools-does-this-server-offer)
- [🏎️ How can I run it?](#️-how-can-i-run-it)
  - [🐋 Using Docker (recommended)](#-using-docker-recommended)
  - [💻 Running locally](#-running-locally)
- [🔌 How to connect](#-how-to-connect)
- [📚 Learn more about MCP](#-learn-more-about-mcp)
- [📄 License](#-license)

## 🛠️ What tools does this server offer?

The server provides two powerful tools that help AI assistants solve real-world problems:

| Tool               | What it can do                                                              |
| ------------------ | --------------------------------------------------------------------------- |
| [Search](docs/search.md) | Search the web via SearXNG for current information, specific resources, or to perform calculations. |
| [Web](docs/web.md) | Access websites and process their content. Can convert pages to markdown for easy reading, get the raw content, or extract links. |

## 🏎️ How can I run it?

### 🐋 Using Docker (recommended)

The server runs in Docker containers to keep things safe and simple. Here's how to get started:

1. [Install Docker](https://docs.docker.com/engine/install/) if you haven't already
2. Create a file called `docker-compose.yml` with:

   ```yaml:docker-compose.yml
   services:
     mcp-server:
       environment:
         # Required: URL for your SearXNG instance's Search API
         - SEARXNG_QUERY_URL=http://searxng:8080
         # Optional: Configure network mode (SSE) for LibreChat etc.
         - SSE_HOST=0.0.0.0
         - SSE_PORT=8080
         # Optional: Set a custom User-Agent for web requests
         - USER_AGENT=MCP-Server/1.0 (github.com/tcpipuk/mcp-server)
       image: ghcr.io/tcpipuk/mcp-server/server:latest
       ports: # Only needed if using SSE_HOST/SSE_PORT
         - "8080:8080" # Expose port 8080 on host
       restart: unless-stopped
       stop_grace_period: 1s

     # Example SearXNG service (optional, adapt as needed)
     # searxng:
     #   environment:
     #     - SEARXNG_BASE_URL=http://searxng:8080 # Ensure SearXNG knows its own URL
     #   image: searxng/searxng:latest
     #   restart: unless-stopped
     #   volumes:
     #     - ./searxng:/etc/searxng:rw
   ```

   > **Important**: You *must* provide the `SEARXNG_QUERY_URL` environment variable, pointing to
   > the Search API endpoint of your SearXNG instance (usually ending in `/` or `/search`).
   >
   > Setting `SSE_HOST` and `SSE_PORT` enables network mode (Server-Sent Events), recommended for
   > multi-container setups like LibreChat. If omitted, the server uses standard I/O.

3. Run `docker compose up -d` to start the server container (and optionally SearXNG).

Most people use this with either:

- [Claude Desktop](https://modelcontextprotocol.io/quickstart/user) - connects directly via stdio
  (omit `SSE_HOST`/`SSE_PORT` in `docker-compose.yml`).
- [LibreChat](https://www.librechat.ai/docs/local) - connects over the network via SSE.

For LibreChat, add this to your `librechat.yaml` (assuming `SSE_PORT=8080`):

```yaml:librechat.yaml
mcpServers:
  mcp-server:
    iconPath: "/path/to/icon.png" # Optional: Custom icon
    label: "MCP Web/Search" # Optional: Custom label shown in UI
    type: sse
    url: http://mcp-server:8080/sse # Adjust host/port if needed
```

### 💻 Running locally

1. Install `uv` (requires Python 3.13+):

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

   > **Note:** If you already have `uv` installed, update it with `uv self update`.

2. Create and activate a virtual environment:

   ```bash
   uv venv
   source .venv/bin/activate  # Linux/macOS
   # or
   .venv\Scripts\activate     # Windows
   ```

3. Install dependencies from the lockfile:

   ```bash
   uv sync
   ```

4. Set required environment variables:

   ```bash
   # Required: URL for your SearXNG instance's Search API
   export SEARXNG_QUERY_URL="http://your-searxng-instance.local:8080"
   # Optional: Custom User-Agent
   export USER_AGENT="CustomAgent/1.0"
   ```

5. Run the server:

   ```bash
   # For network (SSE) mode (e.g., for LibreChat)
   mcp-server --sse-host 0.0.0.0 --sse-port 3001

   # For direct stdio mode (e.g., for Claude Desktop)
   mcp-server
   ```

Available arguments:

- `--sse-host`: SSE listening address (e.g., `0.0.0.0`). Enables SSE mode.
- `--sse-port`: SSE listening port (e.g., `3001`). Enables SSE mode.
- `--user-agent`: Custom User-Agent string (overrides `USER_AGENT` env var).

> **Note**: If neither `--sse-host` nor `--sse-port` are provided (and `SSE_HOST`/`SSE_PORT` env
> vars are not set), the server defaults to `stdio` mode. The `SEARXNG_QUERY_URL` environment
> variable is *always* required.

## 🔌 How to connect

You can connect to the server in two ways:

| Method                    | What it means                                           | When to use it                                  |
| ------------------------- | ------------------------------------------------------- | ----------------------------------------------- |
| Network connection (SSE)  | The server listens on a network port for connections.   | Best for LibreChat or other networked clients.  |
| Direct connection (stdio) | The server communicates directly via standard input/out. | Useful for local testing or Claude Desktop. |

## 📚 Learn more about MCP

Here are a few resources to get you started:

- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [MCP Example Servers](https://github.com/modelcontextprotocol/servers)

## 📄 License

This project is licensed under the GPLv3. See the [LICENSE](LICENSE) file for full details.
