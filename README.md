# MCP Server

This server offers tools that AI assistants can interact with safely to operate external tools and
services using the Model Context Protocol (MCP). It pre-processes data to save tokens and make it
easier for LLMs to understand, and provides informative errors when things go wrong.

1. [🛠️ What tools does this server offer?](#️-what-tools-does-this-server-offer)
2. [🏎️ How can I run it?](#️-how-can-i-run-it)
   1. [🐋 Docker Compose](#-docker-compose)
   2. [💻 Local Development](#-local-development)
3. [🔌 Which connection method should I use?](#-which-connection-method-should-i-use)
4. [📚 Where can I read more about MCP?](#-where-can-i-read-more-about-mcp)
5. [📄 License](#-license)

## 🛠️ What tools does this server offer?

Right now it focuses on helping AIs read web pages, so they can fetch content, find links, and
explore websites on their own:

| Tool | Description |
|------|-------------|
| [fetch](docs/fetch.md) | Fetches and processes content from a given URL. By default, it cleans the content into markdown format, making it easier to read, with an option to return the raw data. |
| [links](docs/links.md) | Extracts and sorts internal links from a webpage. It returns the links along with their frequency and (optionally) the anchor text. |

## 🏎️ How can I run it?

### 🐋 Docker Compose

[Install Docker](https://docs.docker.com/engine/install/) if you haven't already, then put this in
a `docker-compose.yml` and run `docker compose up` to start it:

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

> **Note**: If `SSE_HOST` and/or `SSE_PORT` environment variables are not set, the server will
> automatically use `stdio` mode and listen on standard input/output.

Normally you'd run this alongside [Claude Desktop](https://modelcontextprotocol.io/quickstart/user)
(using stdio mode) or using [LibreChat](https://www.librechat.ai/docs/local) (using SSE mode), just
putting something like this in your `librechat.yaml` to tell it how to talk to this MCP server:

```yaml:librechat.yaml
mcpServers:
  mcp-server:
    iconPath: "/path/to/icon.png"
    type: sse
    url: http://mcp-server:8080/sse
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

## 🔌 Which connection method should I use?

You can run it using Docker, connect through standard input/output on the local machine, or use SSE
over a network, which means it works directly with LibreChat and other MCP-compatible chat systems.

| Method | Best for | Notes |
|--------|----------|--------|
| Standard I/O (stdio) | Local development and testing | Direct process communication. Not recommended for Docker as it requires sharing the Docker socket. |
| Server-Sent Events (SSE) | Production deployment | Runs as a network service. Recommended for Docker and cloud environments. |

## 📚 Where can I read more about MCP?

Here are a few resources to get you started:

- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [MCP Example Servers](https://github.com/modelcontextprotocol/servers)

## 📄 License

This project is licensed under the GPLv3. See the [LICENSE](LICENSE) file for full details.
