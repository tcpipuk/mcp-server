# Use latest Ubuntu LTS as base image
FROM ubuntu:latest

# Install Ubuntu packages
RUN apt-get update && apt-get install -y \
  bash \
  build-essential \
  curl \
  git \
  python-is-python3 \
  python3 \
  python3-pip \
  socat \
  wget \
  && pip install uv \
  && apt-get remove python3-pip \
  && uv self update \
  && apt-get clean && rm -rf /var/cache/apt/* /var/lib/apt/lists/*

# Install Python packages
RUN uv pip install \
  aiodns \
  aiohttp \
  beautifulsoup4 \
  numpy \
  pandas \
  requests \
  ruff
