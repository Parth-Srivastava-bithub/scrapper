# GPU Aggregator - Scraper Worker

Automated scraping and data synchronization worker for GPU cloud providers (**RunPod**, **Novita AI**, and **Vast.ai**). The worker runs on a scheduled cadence to ingest GPU catalogs, pricing, stock levels, and datacenter availability into MongoDB.

> **Guides & Documentation**:
> - Native Local Setup (No Docker): [localsetup.md](localsetup.md)
> - Containerized & Production Startup Guide: [startup.md](startup.md)
> - Architectural Deep-Dive & Browser Automation: [HOW_IT_WORKS.md](HOW_IT_WORKS.md)

---

## Quick Start: Run Immediately with Docker (No Clone Required)

Anyone can start the scraper worker immediately using the pre-built Docker Hub image **`yellowforest/gpu-scraper-worker:latest`** by passing environment variables directly with `-e` flags:

### Linux / macOS (Bash)

```bash
docker run -d \
  --name gpu-scraper-worker \
  --restart unless-stopped \
  -e MONGODB_URI="mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority" \
  -e MONGODB_DB_NAME="gpu_aggregator" \
  -e RUNPOD_API_KEY="your_runpod_api_key_here" \
  -e NOVITA_API_KEY="your_novita_api_key_here" \
  -e CDP_PORT="9222" \
  -e CHROME_HEADLESS="new" \
  -e CHROME_USER_DATA_DIR="/data/chrome-profile" \
  -v scraper_chrome_profile:/data/chrome-profile \
  --shm-size=2g \
  yellowforest/gpu-scraper-worker:latest
```

### Windows (PowerShell)

```powershell
docker run -d `
  --name gpu-scraper-worker `
  --restart unless-stopped `
  -e MONGODB_URI="mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority" `
  -e MONGODB_DB_NAME="gpu_aggregator" `
  -e RUNPOD_API_KEY="your_runpod_api_key_here" `
  -e NOVITA_API_KEY="your_novita_api_key_here" `
  -e CDP_PORT="9222" `
  -e CHROME_HEADLESS="new" `
  -e CHROME_USER_DATA_DIR="/data/chrome-profile" `
  -v scraper_chrome_profile:/data/chrome-profile `
  --shm-size=2g `
  yellowforest/gpu-scraper-worker:latest
```

### View Live Logs

```bash
docker logs -f gpu-scraper-worker
```

---

## Environment Variables Reference

| Variable | Required | Default | Description |
| :--- | :---: | :---: | :--- |
| `MONGODB_URI` | **Yes** | `mongodb://localhost:27017/` | MongoDB connection string (Atlas or self-hosted) |
| `MONGODB_DB_NAME` | No | `gpu_aggregator` | Target MongoDB database name |
| `RUNPOD_API_KEY` | **Yes** | `""` | RunPod API key for GraphQL catalog and pricing queries |
| `NOVITA_API_KEY` | **Yes** | `""` | Novita AI API key for product catalog and datacenter APIs |
| `CDP_PORT` | No | `9222` | Internal Chrome DevTools Protocol port |
| `CHROME_HEADLESS` | No | `new` | Chrome headless mode (`new` / `true` / `false`) |
| `CHROME_USER_DATA_DIR` | No | `/data/chrome-profile` | Container path for persistent Chrome profile & cookies |

---

## Running with Docker Compose (Optional)

If running from the repository, you can use Docker Compose. It supports both an optional `.env` file or direct host environment variables:

```bash
# Start container
docker compose up -d

# View live logs
docker compose logs -f

# Stop container
docker compose down
```

---

## Building and Pushing to Docker Hub

To build and release your own version to Docker Hub:

### 1. Build and Tag

```bash
# Build local image
docker build -t yellowforest/gpu-scraper-worker:latest .
docker build -t yellowforest/gpu-scraper-worker:v1.0.0 .
```

### 2. Push to Docker Hub

```bash
docker login
docker push yellowforest/gpu-scraper-worker:latest
docker push yellowforest/gpu-scraper-worker:v1.0.0
```

### 3. Multi-Architecture Build (`amd64` + `arm64`)

To build a universal image for standard cloud servers (Intel/AMD) and ARM machines (Apple Silicon / AWS Graviton):

```bash
docker buildx build --platform linux/amd64,linux/arm64 \
  -t yellowforest/gpu-scraper-worker:latest \
  --push .
```

---

## Testing & Verification

### 1. Run Automated Unit Tests

```bash
pytest -v
```

### 2. Check Chrome CDP Health inside the Container

```bash
docker exec gpu-scraper-worker curl -s http://127.0.0.1:9222/json/version
```

### 3. Verify Scheduled Scraping Logs

```bash
docker logs -f gpu-scraper-worker
```

Expected startup output:
```text
[ENTRYPOINT] Starting /usr/bin/chromium with CDP on 127.0.0.1:9222...
[ENTRYPOINT] Waiting for Chrome CDP at http://127.0.0.1:9222/json/version...
[ENTRYPOINT] Chrome CDP is healthy and ready on port 9222.
[ENTRYPOINT] Starting application: python scheduler.py
Initializing database...
MongoDB collections and indexes initialized successfully.
Running initial sync...
=========== INITIAL SYNC ===========
========== RunPod Catalog Maintainer ==========
✅ H100 SXM -> H100 SXM (125.0)
...
Upserted 28 GPUs.
========== Novita Catalog Maintainer ==========
Upserted 20 GPUs.
========== RunPod Datacenters Maintainer ==========
Synced 49 RunPod datacenters.
========== Novita Datacenters Maintainer ==========
Synced 24 Novita datacenters.
Initial Sync Complete
Scheduler started...
```

---

## Local Development (Without Docker)

1. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Start Chrome with remote debugging**:
   ```powershell
   & "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\Users\user\chrome-profile"
   ```
3. **Run scheduler**:
   ```bash
   python scheduler.py
   ```
