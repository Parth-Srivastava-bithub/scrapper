FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Install ca-certificates and curl for runpodctl download & HTTPS
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install runpodctl binary (supports amd64 and arm64)
RUN ARCH=$(dpkg --print-architecture) && \
    if [ "$ARCH" = "amd64" ]; then \
        curl -fsSL -o /usr/local/bin/runpodctl https://github.com/runpod/runpodctl/releases/download/v2.9.0/runpodctl-linux-amd64 && \
        chmod +x /usr/local/bin/runpodctl; \
    elif [ "$ARCH" = "arm64" ]; then \
        curl -fsSL -o /usr/local/bin/runpodctl https://github.com/runpod/runpodctl/releases/download/v2.9.0/runpodctl-linux-arm64 && \
        chmod +x /usr/local/bin/runpodctl; \
    fi

WORKDIR /app

# Install dependencies (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source files
COPY database/ /app/database/
COPY maintainers/ /app/maintainers/
COPY scrapers/ /app/scrapers/
COPY scheduler.py /app/scheduler.py

CMD ["python", "scheduler.py"]
