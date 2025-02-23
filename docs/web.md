# Web Tool

1. [What can it do?](#what-can-it-do)
2. [Processing Modes](#processing-modes)
   1. [Markdown Mode (default)](#markdown-mode-default)
   2. [Links Mode](#links-mode)
   3. [Raw Mode](#raw-mode)
3. [Features and Limits](#features-and-limits)
   1. [Content Management](#content-management)
   2. [Safety Features](#safety-features)

A tool that lets AI assistants access and process web content safely. It can convert pages to
markdown, extract links, or get raw content:

![Screenshot of GPT asked to research SSE in the MCP documentation and providing the answer after reading three different pages](./images/web-usage.png)

## What can it do?

When you ask the AI to access a website, it can:

- Convert web pages into clean, readable markdown
- Extract all the links from a page to help navigate
- Get the raw content of any URL
- Process the content to fit your needs

The tool handles all the technical details like following redirects, handling errors, and cleaning
up messy HTML. It's designed to be both powerful and safe - handling complex web content while
staying within resource limits.

## Processing Modes

You can process web content in three ways:

| Mode | What it does | Best for |
|------|-------------|----------|
| `markdown` | Converts the page to clean markdown | Reading articles or documentation |
| `links` | Lists all internal links with their text | Navigating through websites |
| `raw` | Gets the unprocessed content | Accessing APIs or raw data |

### Markdown Mode (default)

The default mode cleans up web pages and converts them to readable markdown:

- Removes adverts, navigation, and other clutter
- Keeps important formatting like headings and lists
- Preserves images and tables
- Falls back to raw content if conversion fails
- Uses smart extraction to focus on the main content

Example output:

```markdown
Contents of https://example.com/article:

# Main Heading

Article content in clean markdown format...

## Subheadings preserved

* Lists kept intact
* With proper formatting

![Images kept with alt text](image.jpg)

| Tables | Converted |
|--------|-----------|
| To     | Markdown  |
```

### Links Mode

This mode helps navigate through websites by extracting and processing links:

- Finds all links on the page
- Converts relative URLs to absolute ones
- Shows which text was used for each link
- Orders links by how often they appear
- Filters out external sites and JavaScript links
- Preserves the first anchor text found for each link
- Handles both relative and absolute URLs safely

Example output:

```markdown
All 45 links found on https://example.com

- Home: https://example.com/
- Products: https://example.com/products
- About Us: https://example.com/about
...
```

### Raw Mode

When you need the original content without processing:

- Gets the exact content from the URL
- Doesn't modify or clean the content
- Useful for APIs or when markdown fails
- Still respects length limits if set
- Great for accessing JSON, XML, or raw code

## Features and Limits

The tool includes several features to make web access safe and reliable:

### Content Management

- **Length Limits**: Control how much content to return
  - Set `max_length` to limit characters (0 means no limit)
  - Complete lines kept in links mode
  - Warning shown when content is truncated:

    ```xml
    <error>Content truncated to 1000 characters</error>
    ```

- **Error Handling**: Clear messages for common issues
  - Connection problems: "Failed to connect to {url}: {reason}"
  - Extraction issues: Falls back to raw content with warning
  - Missing links: "No links found - may need JavaScript or auth"
  - Invalid URLs: Returns helpful error message
  - Timeouts: Shows how long it waited before giving up

### Safety Features

- **Content Processing**
  - Uses `trafilatura` for smart content extraction
  - `BeautifulSoup` for reliable HTML parsing
  - Skips potentially harmful links
  - Handles relative URLs safely

- **Network Safety**
  - Configurable User-Agent string
  - Follows redirects safely
  - Validates URLs before accessing
  - Handles network timeouts gracefully
  - Filters out external and invalid links

The tool aims to balance power with safety - giving AI assistants broad access to web content
while maintaining security and providing clear feedback when things go wrong.
