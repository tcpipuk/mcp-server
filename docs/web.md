# Web Tool

This tool is designed to let the LLM retrieve, extract, and process web content:

![Screenshot of GPT asked to research SSE in the MCP documentation and providing the answer after reading three different pages](./images/web-usage.png)

The tool uses asynchronous HTTP requests via aiohttp, trafilatura for markdown extraction, and
BeautifulSoup for parsing links. The User-Agent string is configurable via the `USER_AGENT`
environment variable (defaults to a Firefox-compatible string).

## Tool Schema

The description provided to the LLM explains why and when to use the tool:

> Use to access the internet when up-to-date information may help. You can navigate documentation,
> or fetch code and data from the web, so use it whenever fresh information from the internet could
> potentially improve the accuracy of your answer to the user.

The arguments available are as follows:

| Argument  | Type    | Required | Default   | Description |
|-----------|---------|----------|-----------|-------------|
| url       | string  | Yes      | -         | URL to process. This can be any public web address, API endpoint, or location of a file on GitHub, etc. |
| mode      | string  | No       | "markdown" | Processing mode. Allowed values: "markdown" (fetch & extract content into markdown), "raw" (retrieve raw content), and "links" (extract internal hyperlinks with anchor text). |
| max_length| integer | No       | 0         | Maximum number of characters to return (0 is unlimited). In links mode, complete lines are added until the limit is met. |

## Content Processing

The tool handles content processing based on the chosen mode.

### Default Processing (mode = "markdown")

- Fetches the URL using aiohttp with the configured User-Agent.
- Uses trafilatura to extract and transform the page content into markdown.
  - Attempts to remove boilerplate such as headers, footers, navigation, and ads.
  - Preserves key formatting like headings, lists, tables, and images.
- If the extraction fails or no content is found, it falls back to the raw response while still
  applying length limiting if specified.

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

### Raw Mode (mode = "raw")

- Fetches the URL and returns its full, unprocessed content.
- No attempts are made to clean up or reformat the content.
- Useful when processing non-HTML content (such as JSON, XML, or code) or when extraction fails.

### Link Processing (mode = "links")

- Fetches the URL and parses the returned HTML using BeautifulSoup (with SoupStrainer for `<a>` tags).
- Converts relative URLs to absolute URLs based on the provided URL.
- Filters out external domains, JavaScript links, and anchor-only references.
- Orders the links by frequency of appearance and preserves the anchor text from the first occurrence.
- The `max_length` parameter is applied such that complete output lines are added until the limit
  is reached.

Example output (with default behavior):

```markdown
All 45 links found on https://example.com

- Home: https://example.com/
- Products: https://example.com/products
- About Us: https://example.com/about
...
```

## Length Limiting

The `max_length` parameter always refers to the number of characters to return:

- In "markdown" and "raw" modes, it acts as a character limit on the final output.
- In "links" mode, it adds complete lines (each showing one link) until adding another full line
  would exceed the specified limit.
- When content is truncated due to the limit, an error message is appended (or prepended in the
  case of markdown extraction failure).

Example error message appended on truncation:

```xml
<error>Content truncated. The output has been limited to {max_length} characters</error>
```

## Error Handling

The Web Tool returns clear and helpful error messages for common problems:

- For network or HTTP issues, the tool provides a readable error response to inform the LLM what
  went wrong. For example:

```json
[
  {
    "type": "text",
    "text": "Failed to connect to http://thisdomaindoesntexist.example: 'Cannot connect to host thisdomaindoesntexist.example:80 ssl:default [Name or service not known]'"
  }
]
```

- If markdown extraction fails in "markdown" mode, the tool will prepend an error message before
  returning the raw content:

```xml
<error>Extraction to markdown failed; returning raw content</error>
```

- In "links" mode, if no links can be extracted (e.g., due to JavaScript requirements or
  authentication), the tool responds with an error message such as:

```markdown
No links found on https://example.com - it may require JavaScript or authentication.
```
