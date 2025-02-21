# MCP Server

MCP Server provides web content retrieval tools over the Model Context Protocol (MCP), supporting
both `stdio` and Server-Sent Events (SSE) transport modes. It enables clients to retrieve and
process web content through a modular, tool-based architecture.

## ✨ Features

- **Asynchronous Operation:** Leverages Python's asynchronous capabilities and `aiohttp` to handle
  multiple requests concurrently.
- **Flexible Transport Modes:** Run the server over standard I/O or via Server-Sent Events (SSE) by
  setting the appropriate environment variables.
- **Tool-based Architecture:** Execute modular tools to offer specific functionalities.

## 🛠️ Available Tools

| Tool  | Description |
|-------|-------------|
| fetch | Fetches and processes content from a given URL. By default, it cleans the content into markdown format, making it easier to read, with an option to return the raw data. |
| links | Extracts and sorts internal links from a webpage. It returns the links along with their frequency and (optionally) the anchor text. |

## 🚀 Quick Start

### 🐋 Docker (Recommended)

Pull and run the stable Docker image:

```bash
docker pull ghcr.io/tcpipuk/mcp-server:latest
```

Create a `docker-compose.yml`:

```yaml:docker-compose.yml
services:
  mcp-fetch:
    environment:
      - SSE_HOST=0.0.0.0
      - SSE_PORT=8080
      - USER_AGENT=CustomAgent/1.0
    image: ghcr.io/tcpipuk/mcp-server:latest
    restart: unless-stopped
    stop_grace_period: 1s
```

> **Note**: If `SSE_HOST` and/or `SSE_PORT` environment variables are not set, the server will
> automatically use `stdio` mode and listen on standard input/output.

### 🔗 LibreChat Integration

Add this to your LibreChat configuration:

```yaml:librechat.yaml
mcpServers:
  fetch:
    iconPath: ""
    type: sse
    url: http://mcp-fetch:8080/sse
```

### 💻 Local Development

1. Install `uv` (requires Python 3.13+):

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

   > **Note:** If you already have `uv` installed, you can update it by running:
   >
   > ```bash
   > uv self update
   > ```

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

4. Run the server:

   ```bash
   mcp-server --sse-host 0.0.0.0 --sse-port 3001 --user-agent "CustomAgent/1.0"
   ```

Available arguments:

- `--sse-host`: SSE listening address (e.g. `0.0.0.0`)
- `--sse-port`: SSE listening port (e.g. `3001`)
- `--user-agent`: Custom User-Agent string for HTTP requests

> **Note**: If either of the SSE arguments are not provided (or the `SSE_HOST` or `SSE_PORT`
> environment variables are not set) the server will automatically assume `stdio` mode and
> listen on standard I/O.

## 📦 Resources

- Repository: <https://github.com/tcpipuk/mcp-server>
- Docker Images: <https://github.com/tcpipuk/mcp-server/pkgs/container/mcp-server>
- MCP Python SDK: <https://github.com/modelcontextprotocol/python-sdk>
- MCP Specification: <https://spec.modelcontextprotocol.io/>

## 📄 License

This project is licensed under the GPLv3. See the [LICENSE](LICENSE) file for full details.
