# Sandbox Tool

1. [What can it do?](#what-can-it-do)
2. [How does it work?](#how-does-it-work)
3. [Available Tools](#available-tools)
   1. [Python Environment](#python-environment)
   2. [Development Tools](#development-tools)
   3. [System Tools](#system-tools)
4. [Security and Isolation](#security-and-isolation)
5. [Workspace Management](#workspace-management)

A secure environment that lets AI assistants run code and commands to help solve your problems.
It runs in a separate Docker container to keep your system safe while still being powerful enough
to handle complex tasks.

![Screenshot showing GPT writing and running a Python script to analyse data](./images/sandbox-usage.png)

## What can it do?

Whether you're analysing data, debugging network issues, or improving code quality, the sandbox
gives AI assistants the tools they need to help. They can write and run Python scripts, process
data with powerful libraries like pandas, test network connectivity, and manage long-running tasks.

For example, you might ask:

- "Write a Python script to analyse this CSV data"
- "Help me understand why this website isn't responding"
- "Check if my code follows best practices"
- "Download and process these log files"
- "Set up a screen session to monitor a long process"

## How does it work?

When you ask for help, the AI works in a dedicated `/workspace` directory that persists between
commands. This lets it build up complex solutions over time, writing code to files, testing them,
and refining them until they work perfectly. You'll see the results of each step, with clear
explanations of what's happening and any issues that need fixing.

For Python tasks, the AI writes complete, well-structured scripts rather than running code
directly. It uses powerful libraries like pandas for efficient data processing, and automatically
checks code quality and formatting to ensure everything is clean and maintainable.

Need to run something that takes a while? The AI can set up screen sessions that keep running
even after the command finishes. It gives them descriptive names so you can find them easily,
monitors their progress, and helps you manage the output. When the task is done, it'll clean up
after itself to keep your workspace tidy.

## Available Tools

The sandbox comes equipped with everything needed for data analysis, development, and system
investigation:

### Python Environment

Python 3.13 forms the core of the sandbox, with powerful packages for data analysis and network
tasks. Pandas and numpy handle complex calculations and data processing, while libraries like
requests and aiohttp make it easy to work with web services and APIs.

### Development Tools

To help maintain code quality, the sandbox includes modern development tools like git for version
control and ruff for linting and formatting. The screen utility lets you manage long-running
processes that need to persist between commands.

### System Tools

For investigating network issues or managing files, the sandbox provides a full suite of Unix
tools. You can test connectivity with ping and traceroute, look up DNS records with dig, or
download files with wget and curl. The tree command helps visualise directory structures, making
it easy to keep track of your files.

## Security and Isolation

Security is built into every aspect of the sandbox. It runs in its own Docker container,
completely isolated from your system's files and processes. While it can make outbound network
connections by default (which you can restrict further with Docker or firewall rules if needed),
no inbound connections are allowed. Resource limits on CPU and memory prevent runaway processes,
and automatic cleanup between sessions keeps things fresh.

## Workspace Management

The `/workspace` directory is your AI assistant's home base. Each session starts fresh, but files
you create stay available for future use. This persistence lets you build up complex solutions
over time, using screen sessions for long-running tasks and organizing work into folders as
needed. When you're done, old files and sessions can be cleaned up to keep things tidy.

The sandbox strikes a careful balance between power and safety - giving AI assistants the tools
they need to help you while keeping your system secure. Just describe what you need help with,
and the AI will use the right tools to solve your problem.
