# Search Tool

- [Capabilities](#capabilities)
- [Refining the Search](#refining-the-search)
  - [The Query (`q`)](#the-query-q)
  - [Filtering by Time (`time_range`)](#filtering-by-time-time_range)
  - [Content Safety (`safesearch`)](#content-safety-safesearch)
- [Technical Details](#technical-details)

Provides the AI assistant with web search capabilities via a SearXNG instance. It allows the AI to
fetch current information, look up specific resources, and perform other search-related tasks.

## Capabilities

The tool enables the AI assistant to perform tasks requiring external information lookup, such as:

- Finding details on current events or recent developments.
- Retrieving specific technical documentation or code examples.
- Searching for various online content types (e.g., images, news).
- Accessing specialised resources like scientific papers, package repositories (PyPI, npm), or Q&A
  sites (Stack Exchange).
- Using WolframAlpha for calculations or fetching random data (UUIDs, numbers).
- Calculating text hashes.

## Refining the Search

The AI can tailor searches using the available parameters:

### The Query (`q`)

The primary search input. Supports standard queries and SearXNG's specific syntax:

- **Bang Prefixes (`!`):** Focuses the search on categories or engines (e.g. `!news`, `!images`,
  `!it`, `!repos`, `!pypi`, `!wa`, `!re`). Prefixes can be chained (e.g., `!it !q&a python async`).
- **Keywords (No `!`):** Executes specific actions like calculations (`avg 1 2 3`), random data
  generation (`random uuid`), or hashing (`sha512 text`).

### Filtering by Time (`time_range`)

Restricts results to a specific period (`day`, `month`, `year`), where supported by the underlying
SearXNG engines.

### Content Safety (`safesearch`)

Adjusts the filtering level for potentially explicit content: `0` (Off), `1` (Moderate - default),
or `2` (Strict), engine permitting.

## Technical Details

Key aspects of the tool's operation:

- **Backend:** Relies on the SearXNG instance specified by the server's `SEARXNG_QUERY_URL`
  environment variable.
- **Output Format:** Returns results exclusively in JSON format for straightforward parsing by the AI.
- **Request Handling:** Uses the common `get_request` helper function (shared with the `web` tool)
  for managing HTTP requests, including redirects, timeouts, and connection errors. Errors are
  reported back to the AI.
- **Parameter Exposure:** Only the parameters defined in `tools.yaml` (`q`, `time_range`,
  `safesearch`) are available to the AI.

This tool gives the AI assistant a mechanism to query a SearXNG instance, enabling access to
real-time web information and specialised search functions.
