# Links Tool

1. [Tool Schema](#tool-schema)
2. [Link Processing](#link-processing)
   1. [Example Output](#example-output)
3. [Error Handling](#error-handling)

The `links` tool provides web crawling capabilities to LLMs over MCP.

It uses `aiohttp` for async HTTP requests and `BeautifulSoup` for HTML parsing, running
asynchronously to handle concurrent requests efficiently. For performance, it uses `SoupStrainer`
to parse only `<a>` tags and `urllib.parse` for robust URL handling.

The tool's User-Agent string can be customised via the `USER_AGENT` environment variable
(defaults to a Firefox-compatible string).

## Tool Schema

The description of the tool provided to the LLM explains why it should use the tool:

> Fetch a list of links from a webpage. Useful to discover related pages and understand the
> structure when exploring a website. By default, includes the text from the link, which may
> provide helpful context. You could then `fetch` URLs to see the content, as you're not limited
> in how many tools you can use.

The arguments it is allowed to provide are:

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| url | string | Yes | - | URL to scrape for links |
| max_links | integer | No | 100 | Maximum number of URLs to return |
| titles | boolean | No | true | Include the anchor text for each link |

## Link Processing

The tool processes links in several stages to provide clean, relevant results:

1. **Content Retrieval**
   - Fetches the URL using `aiohttp` with configurable User-Agent
   - Uses `BeautifulSoup` with `SoupStrainer` to efficiently parse only `<a>` tags

2. **Link Processing**
   - Converts relative URLs to absolute using the base URL
   - Filters out external domains to focus on site structure
   - Removes javascript: links and anchor-only references
   - Tracks frequency of each URL and its first appearance

3. **Result Ordering**
   - Orders links by frequency (most frequent first)
   - Uses original appearance order as secondary sort
   - Preserves anchor text from first occurrence of each URL
   - Applies `max_links` limit only after processing all links

### Example Output

With titles enabled (default):

```markdown
20 of 45 links found on https://example.com

- Home: https://example.com/
- Products: https://example.com/products
- About Us: https://example.com/about
```

With titles disabled:

```markdown
20 of 45 links found on https://example.com

- https://example.com/
- https://example.com/products
- https://example.com/about
```

## Error Handling

The tool returns readable errors for most common issues to help inform the LLM of what went wrong:

```json
[
  {
    "type": "text",
    "text": "Failed to connect to http://thisdomaindoesntexist.example: 'Cannot connect to host thisdomaindoesntexist.example:80 ssl:default [Name or service not known]'"
  }
]
```

If no links could be found, it returns:

```markdown
No links read on https://example.com - it may require JavaScript or authentication.
```
