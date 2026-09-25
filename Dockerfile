FROM python:3.12-slim-bookworm

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies, Chromium, fonts, and utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-sandbox \
    curl \
    ca-certificates \
    procps \
    fonts-liberation \
    fonts-noto-color-emoji \
    libasound2 \
    libgbm1 \
    libnss3 \
    && rm -rf /var/lib/apt/lists/*

# Install runpodctl CLI for datacenter discovery
RUN ARCH=$(dpkg --print-architecture) && \
    if [ "$ARCH" = "amd64" ]; then \
        curl -sSL -o /usr/local/bin/runpodctl https://github.com/runpod/runpodctl/releases/download/v2.9.0/runpodctl-linux-amd64 && \
        chmod +x /usr/local/bin/runpodctl; \
    elif [ "$ARCH" = "arm64" ]; then \
        curl -sSL -o /usr/local/bin/runpodctl https://github.com/runpod/runpodctl/releases/download/v2.9.0/runpodctl-linux-arm64 && \
        chmod +x /usr/local/bin/runpodctl; \
    fi || true

# Set up working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files and scripts
COPY database/ /app/database/
COPY maintainers/ /app/maintainers/
COPY scrapers/ /app/scrapers/
COPY scheduler.py /app/scheduler.py
COPY entrypoint.sh /app/entrypoint.sh

# Ensure proper permissions and Unix line endings on entrypoint script
RUN sed -i 's/\r$//' /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh && \
    mkdir -p /data/chrome-profile

# Environment variable defaults for Chrome and CDP
ENV CHROME_USER_DATA_DIR=/data/chrome-profile \
    CDP_PORT=9222 \
    CDP_HOST=127.0.0.1 \
    CHROME_CDP_URL=http://127.0.0.1:9222 \
    CHROME_HEADLESS=new

# Persistent volume for Chrome profile session / cookies
VOLUME ["/data/chrome-profile"]

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "scheduler.py"]
