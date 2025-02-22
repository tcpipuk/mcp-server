# Python Tool

1. [Tool Schema](#tool-schema)
2. [Execution Mode](#execution-mode)
   1. [Resource Limits](#resource-limits)
   2. [Available Packages](#available-packages)
3. [Linting Mode](#linting-mode)
4. [Error Handling](#error-handling)

The `python` tool provides code execution and linting capabilities to LLMs over MCP:

![Screenshot of GPT asked to perform a complex calculation then estimating π using Monte Carlo simulation](./images/python-usage.png)

It uses a dedicated virtual environment with pre-installed packages, running in a sandboxed
environment with resource limits to ensure safe execution.

## Tool Schema

The description of the tool provided to the LLM explains why it should use the tool:

> Execute or lint Python code in a resource-limited sandbox. It has internet access, with aiodns,
> aiohttp, bs4, numpy, pandas, and requests installed, so you can now test and solve a number of
> problems without needing to directly calculate it yourself. Depending on your input parameters,
> this tool either runs the code or lints with Ruff, so you can test code before running, or use
> Ruff to help debugging if you get errors. The user can see the code you've submitted and the raw
> returned response, but it's good etiquette to briefly summarise after using this tool what you
> asked for and got back.

The arguments it is allowed to provide are:

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| code | string | Yes | - | Python code to use |
| timeout | integer | No | 10 | Timeout in seconds for execution (ignored when linting) |
| lint | boolean | No | false | Lint the code using Ruff instead of executing it |

## Execution Mode

When `lint` is false, the tool executes the provided Python code in a sandboxed environment.
The code runs in a dedicated virtual environment with pre-installed packages, isolated from the
main application.

### Resource Limits

The sandbox enforces the following limits:

- Memory: 2GB maximum
- CPU Time: 600 seconds (10 minutes)
- Process Creation: Limited to prevent fork bombs
- File Size: 50MB maximum output
- Core Dumps: Disabled

### Available Packages

The sandbox provides these pre-installed packages:

- `aiodns`, `aiohttp` - Async network operations
- `bs4` - HTML parsing
- `numpy`, `pandas` - Data processing
- `requests` - HTTP client
- `ruff` - Python linter

## Linting Mode

When `lint` is true:

- Uses Ruff to check code quality
- Returns JSON-formatted output of any issues found
- Reports "No issues found!" when code passes all checks
- Ignores the `timeout` parameter (linting isn't time-limited)

Example linting output:

```json
[
  {
    "code": "E101",
    "message": "Indentation error: unexpected indent",
    "location": {
      "line": 2,
      "column": 3
    }
  }
]
```

## Error Handling

The tool captures both stdout and stderr, returning them in the response. Common errors include:

```python
# Timeout
"Execution timed out"

# Resource limits
"MemoryError: ..."

# Import errors
"ImportError: No module named '...'"

# Syntax errors
"SyntaxError: invalid syntax"
```

Errors are always included in the output, whether from linting or execution, to help diagnose issues.
