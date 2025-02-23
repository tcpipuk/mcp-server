# MCP Server

A server that lets AI assistants like Claude safely use external tools - like running Python code or
accessing websites. It processes data to make it easier for AI to understand, and provides helpful
error messages when things go wrong, so bots are more empowered to solve their own problems.

1. [🛠️ What tools does this server offer?](#️-what-tools-does-this-server-offer)
2. [🏎️ How can I run it?](#️-how-can-i-run-it)
   1. [🐋 Using Docker (recommended)](#-using-docker-recommended)
   2. [💻 Running locally](#-running-locally)
3. [🔌 How to connect](#-how-to-connect)
4. [📚 Learn more about MCP](#-learn-more-about-mcp)
5. [📄 License](#-license)

## 🛠️ What tools does this server offer?

Once running, your AI assistant will be able to:

| Tool | What it can do |
|------|-------------|
| [Python](docs/python.md)| Run Python code safely in a sandbox. Includes popular packages like numpy and pandas for data analysis, and can either run code or check it for errors. |
| [Web](docs/web.md) | Access websites and process their content. Can convert pages to markdown for easy reading, get the raw content, or extract links to help navigate through documentation. |

## 🏎️ How can I run it?

### 🐋 Using Docker (recommended)

1. [Install Docker](https://docs.docker.com/engine/install/) if you haven't already
2. Create a file called `docker-compose.yml` with:

   ```yaml:docker-compose.yml
   services:
   mcp-server:
      environment:
         - SSE_HOST=0.0.0.0
         - SSE_PORT=8080
         - USER_AGENT=CustomAgent/1.0
      image: ghcr.io/tcpipuk/mcp-server:latest
      restart: unless-stopped
      stop_grace_period: 1s
   ```

3. Run `docker compose up` to start the server

> **Note**: The server will automatically use network mode (SSE) when you set `SSE_HOST` and
> `SSE_PORT`. This is what you want for using it with LibreChat.

Most people use this with either:

- [Claude Desktop](https://modelcontextprotocol.io/quickstart/user) - connects directly to your computer
- [LibreChat](https://www.librechat.ai/docs/local) - connects over the network

For LibreChat, add this to your `librechat.yaml` to connect:

```yaml:librechat.yaml
mcpServers:
  mcp-server:
    iconPath: "/path/to/icon.png"
    type: sse
    url: http://mcp-server:8080/sse
```

### 💻 Running locally

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

## 🔌 How to connect

You can connect to the server in two ways:

| Method | What it means | When to use it |
|--------|---------------|----------------|
| Network connection (SSE) | The server runs as a service that other apps can connect to | Best for most users - especially with LibreChat |
| Direct connection (stdio) | The server runs directly on your computer | Useful for testing or development |

## 📚 Learn more about MCP

Here are a few resources to get you started:

- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [MCP Example Servers](https://github.com/modelcontextprotocol/servers)

## 📄 License

This project is licensed under the GPLv3. See the [LICENSE](LICENSE) file for full details.
