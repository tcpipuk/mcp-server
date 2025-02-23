# Python Tool

1. [What can it do?](#what-can-it-do)
2. [Available Packages](#available-packages)
3. [Running Code](#running-code)
4. [Safety and Limits](#safety-and-limits)
5. [Error Handling](#error-handling)
6. [Technical Details](#technical-details)
   1. [Sandbox Environment](#sandbox-environment)
   2. [Process Management](#process-management)
   3. [Code Quality Tools](#code-quality-tools)
   4. [Resource Management](#resource-management)

A tool that lets AI assistants run Python code safely. It includes popular data science packages
and can either run code or check it for errors:

![Screenshot of GPT asked to perform a complex calculation then estimating π using Monte Carlo simulation](./images/python-usage.png)

## What can it do?

When you ask the AI to use Python, it can:

- Run calculations and process data
- Create visualisations and charts
- Access the internet to fetch data
- Check code for errors before running it

The tool can either run your code directly or lint it first to catch potential issues. Linting is
particularly useful when debugging or when you want to ensure code quality before running.

## Available Packages

The tool comes with these useful packages pre-installed:

| Package | What it's for |
|---------|--------------|
| `numpy`, `pandas` | Working with data - especially tables and calculations |
| `requests`, `aiohttp` | Fetching data from the internet |
| `bs4` (BeautifulSoup) | Processing web pages |
| `ruff` | Checking code for errors |

All packages run in a dedicated virtual environment to ensure consistency and security.

## Running Code

The AI can run Python code by providing:

- The code to run (required)
- How long to let it run for (optional, defaults to 10 seconds)
- Whether to check the code for errors instead of running it (optional)

The code runs in a temporary directory that's cleaned up afterwards, and only has access to a
limited set of environment variables (`LANG`, `TZ`, `PYTHONPATH`, and a few others) for security.

## Safety and Limits

To keep things safe and fast, the tool enforces strict resource limits:

- Memory usage: Up to 2GB (via `RLIMIT_AS`)
- CPU time: Up to 10 minutes (via `RLIMIT_CPU`)
- Process creation: Limited to 50 processes (via `RLIMIT_NPROC`)
- File operations: Up to 50MB (via `RLIMIT_FSIZE`)
- Core dumps: Disabled (via `RLIMIT_CORE`)

These limits are enforced using Linux resource limits (`setrlimit`) and can't be bypassed by the
running code.

## Error Handling

The tool captures both stdout and stderr, providing detailed error messages when things go wrong:

- Timeouts: `Execution terminated after {timeout} seconds`
- Memory limits: `MemoryError: ...`
- Import errors: `ImportError: No module named '...'`
- Syntax errors: `SyntaxError: invalid syntax`
- File system errors: `File system error: ...`
- Process errors: `Process exited with code {code}`

When using linting mode, errors are returned in a structured JSON format:

```json
[
  {
    "code": "E101",
    "message": "Indentation contains mixed spaces and tabs",
    "location": {
      "line": 2,
      "column": 3
    }
  }
]
```

## Technical Details

The tool uses several layers of protection to ensure safe code execution:

### Sandbox Environment

- Runs in an isolated temporary directory
- Uses a dedicated virtual environment
- Cleans up all temporary files after execution
- Restricts environment variables to a safe allowlist

### Process Management

- Uses `asyncio` for non-blocking execution
- Supports graceful timeout handling
- Captures and formats both stdout and stderr
- Returns structured error information

### Code Quality Tools

- Uses Ruff for linting with most rules enabled:
  - All standard Python style checks
  - Common error patterns
  - Code complexity issues
  - Type checking hints
- Ignores specific rules that aren't relevant:
  - `COM812`: Missing trailing comma
  - `CPY`: Copyright notice
  - `D100`: Missing docstring at the top of the file
  - `D203`, `D213`: Docstring formatting
  - `FBT`: Boolean arguments in function definitions
  - `RUF029`: Async methods that don't use `await`

### Resource Management

- Uses Linux kernel resource limits
- Prevents fork bombs and memory exhaustion
- Handles cleanup even after crashes
- Supports both synchronous and asynchronous execution

The tool is designed to be both secure and helpful - it provides detailed error messages and
linting suggestions while ensuring that code can't harm the system or use excessive resources.
