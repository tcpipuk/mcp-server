# Fetch Tool

1. [Tool Schema](#tool-schema)
2. [Content Processing](#content-processing)
   1. [Default Processing (raw=false)](#default-processing-rawfalse)
   2. [Raw Mode (raw=true)](#raw-mode-rawtrue)
   3. [Length Limiting](#length-limiting)
3. [Error Handling](#error-handling)

The `fetch` tool provides web content retrieval capabilities to LLMs over MCP.

It uses `aiohttp` for async HTTP requests and `trafilatura` for content extraction, running
asynchronously to handle concurrent requests efficiently.

The tool's User-Agent string can be customised via the `USER_AGENT` environment variable
(defaults to a Firefox-compatible string).

## Tool Schema

The description of the tool provided to the LLM explains why it should use the tool:

> Read content from a real internet URL. By default, this tool attempts to clean pages and format
> in markdown for efficiency, removing non-content like navigation or ads to make your job easier.
> If asked to find something on a website, you can combine with the `links` tool to explore a
> website to find the content you need.

The arguments it is allowed to provide are:

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| url | string | Yes | - | URL to fetch |
| max_length | integer | No | 0 | Max characters to return (0 is unlimited) |
| raw | boolean | No | false | Get raw content instead of cleaning/extracting to markdown |

## Content Processing

### Default Processing (raw=false)

The tool:

1. Fetches the URL using `aiohttp` with configurable User-Agent
2. Uses `trafilatura` to extract and format content:
   - Attempts to removes boilerplate (headers, footers, ads)
   - Converts main article content to markdown (preserving headings, lists, tables, etc)

> **Note:** If no content is found, or trafilatura fails to extract content properly, the tool will
> return the raw response (HTML or otherwise) but still obey any `max_length` limit.

Example output:

```markdown
Contents of https://example.com/article:

# Article Title

Main content paragraphs formatted in clean markdown...

## Subheadings preserved

* Lists maintained
* With proper formatting

![Images kept with alt text](image.jpg)

| Tables | Converted |
|--------|-----------|
| To     | Markdown  |
```

### Raw Mode (raw=true)

When `raw` is true:

- Returns the raw response (HTML or otherwise)
- No content cleaning or extraction
- Useful when page isn't HTML or trafilatura fails to extract content properly

### Length Limiting

The `max_length` parameter:

- Truncates output to specified character length
- Applies after processing (markdown conversion or raw)
- Adds warning message when content is truncated
- Default 0 means no limit

## Error Handling

The tool returns readable errors for most common HTTP/network issues to help inform the LLM of what
went wrong, e.g.

```json5
[
  {
    "type": "text",
    "text": "Failed to connect to http://thisdomaindoesntexist.example: 'Cannot connect to host thisdomaindoesntexist.example:80 ssl:default [Name or service not known]'"
  }
]
```

When Markdown extraction fails, it'll prepend this before the raw response:

```xml
<error>Extraction to markdown failed; returning raw content</error>
```

Likewise, if `max_length` is specified and the content is truncated, it'll append this after the
truncated content:

```xml
<error>Content truncated. The output has been limited to {max_length} characters</error>
```
